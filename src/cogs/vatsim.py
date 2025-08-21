# vatsim_cog.py
import os
import math
import time
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from cachetools import TTLCache
import settings

VATSIM_URL = "https://data.vatsim.net/v3/vatsim-data.json"

# You can override this if AirportDB changes their path:
# e.g. AIRPORTDB_URL_TMPL="https://airportdb.io/api/airport/{icao}"
AIRPORTDB_URL_TMPL = "https://airportdb.io/api/v1/airport/{icao}"


def inject_api_token(url: str) -> str:
    """
    Injects the API token into the URL if it's set in the environment.
    This is useful for APIs that require an API key.
    """
    api_token = settings.AIRPORTS_KEY
    if api_token:
        return f"{url}?apiToken={api_token}"
    return url


# ----------------- helpers -----------------
def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = R_km * c
    return km * 0.539957  # km -> NM


def fmt_freq_mhz(freq: Optional[str | float]) -> str:
    """
    VATSIM v3 feed provides controller/ATIS frequency as a string in MHz.
    We DO NOT divide; we just normalize and append 'MHz'.
    """
    if freq in (None, "", 0):
        return "—"
    try:
        return f"{float(str(freq)):.3f} MHz"
    except Exception:
        s = str(freq).strip()
        s = s.replace("MHZ", "MHz")
        return s if s.endswith("MHz") else f"{s} MHz"


def controller_kind(callsign: str, icao: str) -> str:
    lower = callsign.upper()
    if not lower.startswith(icao.upper()):
        return "ATC"
    if "_DEL" in lower: return "DEL"
    if "_GND" in lower: return "GND"
    if "_TWR" in lower: return "TWR"
    if "_APP" in lower: return "APP"
    if "_DEP" in lower: return "DEP"
    if "_ATIS" in lower: return "ATIS"
    return "ATC"


def is_dest_atc_online(icao: str, controllers: List[dict], atis: List[dict]) -> tuple[bool, List[str]]:
    icao_up = icao.upper()
    online = []
    for c in controllers:
        cs = (c.get("callsign") or "").upper()
        if cs.startswith(icao_up + "_"):
            online.append(f"{cs} {fmt_freq_mhz(c.get('frequency'))}")
    for a in atis:
        cs = (a.get("callsign") or "").upper()
        if cs.startswith(icao_up + "_"):
            online.append(f"{cs} {fmt_freq_mhz(a.get('frequency'))}")
    return (len(online) > 0, online)


# ----------------- AirportDB lookup (cached) -----------------
def _pick(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


class AirportLookup:
    """
    Fetch airport info from airportdb.io by ICAO and cache it.
    Positive cache: 30 days. Negative cache: 1 hour.
    Tries to be resilient to different key names.
    """

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self._pos = TTLCache(maxsize=20000, ttl=30 * 24 * 3600)  # 30 days
        self._neg = TTLCache(maxsize=20000, ttl=3600)  # 1 hour
        self._locks: Dict[str, asyncio.Lock] = {}

    def _lock_for(self, icao: str) -> asyncio.Lock:
        icao = icao.upper()
        if icao not in self._locks:
            self._locks[icao] = asyncio.Lock()
        return self._locks[icao]

    async def get(self, icao: str) -> Optional[dict]:
        icao = icao.upper().strip()
        if icao in self._pos:
            return self._pos[icao]
        if icao in self._neg:
            return None

        async with self._lock_for(icao):
            if icao in self._pos:
                return self._pos[icao]
            if icao in self._neg:
                return None

            # Fetch from AirportDB API
            url = AIRPORTDB_URL_TMPL.format(icao=icao)
            url = inject_api_token(url)
            headers = {"Accept": "application/json"}
            async with self._session.get(url, headers=headers) as resp:
                if resp.status == 404:
                    self._neg[icao] = True
                    return None
                resp.raise_for_status()
                raw = await resp.json()

            # Some APIs return a list; if so, grab first match
            if isinstance(raw, list) and raw:
                raw = raw[0]
            if not isinstance(raw, dict):
                self._neg[icao] = True
                return None

            # Try common key variants (AirportDB, OurAirports, etc.)
            lat = _pick(raw, "lat", "latitude", "latitude_deg", "latitudeAirport")
            lon = _pick(raw, "lon", "longitude", "longitude_deg", "longitudeAirport")
            name = _pick(raw, "name", "airportName", "nameAirport")
            ident = _pick(raw, "icao", "ident", "codeIcao", "codeIcaoAirport", default=icao)
            elev = _pick(raw, "elevation_ft", "elevationFeet", "elevation", "elevation_ft_agl")

            data = {"icao": ident, "name": name or ident, "lat": float(lat), "lon": float(lon), "elev_ft": elev}
            self._pos[icao] = data
            return data


# ----------------- watcher state -----------------
@dataclass
class WatchEntry:
    user_id: int
    callsign: str
    dest_icao: str
    created_ts: float
    notified_now: bool
    active: bool = True


# ----------------- Cog -----------------
class VatsimCog(commands.Cog):
    """VATSIM ATC/traffic commands + destination ATC watcher (AirportDB + correct MHz formatting)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12))
        self.airports = AirportLookup(self.http)

        self._vatsim_cache: Optional[dict] = None
        self._vatsim_cache_at: float = 0.0

        # (discord_user_id, callsign) -> WatchEntry
        self._watchers: Dict[Tuple[int, str], WatchEntry] = {}

        self.poll_vatsim.start()

    async def cog_unload(self):
        self.poll_vatsim.cancel()
        await self.http.close()

    # -------- VATSIM feed (cached 60s) --------
    async def _get_vatsim_data(self) -> dict:
        if self._vatsim_cache and (time.time() - self._vatsim_cache_at) < 60:
            return self._vatsim_cache
        headers = {"User-Agent": "DiscordBot-MSFS/VATSIM", "Accept": "application/json"}
        async with self.http.get(VATSIM_URL, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
        self._vatsim_cache = data
        self._vatsim_cache_at = time.time()
        return data

    def _find_pilot_by_callsign(self, data: dict, callsign: str) -> Optional[dict]:
        target = callsign.upper().strip()
        for p in data.get("pilots", []):
            if (p.get("callsign") or "").upper().strip() == target:
                return p
        return None

    # ----------------- /vatsim_atc -----------------
    @app_commands.command(name="vatsim_atc", description="Show VATSIM ATC online for an airport (e.g., LPPT)")
    @app_commands.describe(icao="Airport ICAO (e.g., LPPT)")
    async def vatsim_atc(self, interaction: discord.Interaction, icao: str):
        apt = await self.airports.get(icao)
        if not apt:
            await interaction.response.send_message(
                f"Airport `{icao.upper()}` not found on AirportDB.", ephemeral=True
            )
            return

        data = await self._get_vatsim_data()
        ctrls = data.get("controllers", [])
        atis_list = data.get("atis", [])

        icao_up = apt["icao"].upper()
        relevant = [c for c in ctrls if (c.get("callsign", "").upper().startswith(icao_up + "_"))]
        atis = [a for a in atis_list if (a.get("callsign", "").upper().startswith(icao_up + "_"))]

        embed = discord.Embed(
            title=f"VATSIM ATC – {icao_up}",
            description=f"{apt['name']} ({apt['lat']:.4f}, {apt['lon']:.4f})",
            color=discord.Color.blue()
        )

        if relevant:
            for c in sorted(relevant, key=lambda x: x.get("callsign", "")):
                kind = controller_kind(c.get("callsign", ""), icao_up)
                embed.add_field(
                    name=f"{c.get('callsign', '')} ({kind})",
                    value=(
                        f"**Freq:** {fmt_freq_mhz(c.get('frequency'))}\n"
                        f"**Controller:** {c.get('name') or '—'}\n"
                        f"**Rating:** {c.get('rating') or '—'}\n"
                        f"**Updated:** {c.get('last_updated') or '—'}"
                    ),
                    inline=False
                )
        else:
            embed.add_field(name="ATC", value="No ATC online.", inline=False)

        for a in atis:
            code = a.get("atis_code") or "—"
            lines = a.get("text_atis") or []
            text = "\n".join(lines[:6])
            embed.add_field(
                name=f"{a.get('callsign', '')} (ATIS {code})",
                value=f"**Freq:** {fmt_freq_mhz(a.get('frequency'))}\n```\n{text}\n```",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # ----------------- /vatsim_nearby -----------------
    @app_commands.command(name="vatsim_nearby", description="Show aircraft near an airport within a radius (NM)")
    @app_commands.describe(icao="Airport ICAO (e.g., LPPT)", radius_nm="Radius in NM (5-300)")
    async def vatsim_nearby(self, interaction: discord.Interaction, icao: str,
                            radius_nm: app_commands.Range[int, 5, 300] = 80):
        apt = await self.airports.get(icao)
        if not apt:
            await interaction.response.send_message(
                f"Airport `{icao.upper()}` not found on AirportDB.", ephemeral=True
            )
            return

        data = await self._get_vatsim_data()
        pilots = data.get("pilots", [])
        lat0, lon0 = apt["lat"], apt["lon"]

        nearby = []
        for p in pilots:
            plat = p.get("latitude")
            plon = p.get("longitude")
            if plat is None or plon is None:
                continue
            dnm = haversine_nm(lat0, lon0, float(plat), float(plon))
            if dnm <= float(radius_nm):
                nearby.append((dnm, p))
        nearby.sort(key=lambda x: x[0])
        take = nearby[:20]

        if not take:
            await interaction.response.send_message(
                f"No aircraft within {radius_nm} NM of {apt['icao']} ({apt['name']})."
            )
            return

        embed = discord.Embed(
            title=f"VATSIM Nearby – {apt['icao']} ({apt['name']})",
            description=f"Within **{radius_nm} NM** · Showing {len(take)} · ({lat0:.4f}, {lon0:.4f})",
            color=discord.Color.green()
        )

        for dnm, p in take:
            cs = p.get("callsign", "—")
            gs = p.get("groundspeed", "—")
            alt = p.get("altitude", "—")
            hdg = p.get("heading", "—")
            fp = p.get("flight_plan") or {}
            dep = fp.get("departure") or "—"
            arr = fp.get("arrival") or "—"
            embed.add_field(
                name=f"{cs} · {dnm:.1f} NM",
                value=f"**ALT:** {alt} ft · **GS:** {gs} kt · **HDG:** {hdg}° · **Route:** {dep}→{arr}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # ----------------- /vatsim_watch -----------------
    @app_commands.command(
        name="vatsim_watch",
        description="Watch your VATSIM destination and DM you when ATC is online."
    )
    @app_commands.describe(callsign="Your VATSIM callsign, e.g., TAP123")
    async def vatsim_watch(self, interaction: discord.Interaction, callsign: str):
        await interaction.response.defer(ephemeral=True)
        data = await self._get_vatsim_data()
        pilot = self._find_pilot_by_callsign(data, callsign)
        if not pilot:
            await interaction.followup.send(
                f"I can't find `{callsign}` on VATSIM right now. Connect and file a FP, then try again.")
            return

        fp = pilot.get("flight_plan") or {}
        dest = (fp.get("arrival") or "").upper().strip()
        if not dest or len(dest) != 4:
            await interaction.followup.send(
                f"Your flight plan for `{callsign}` has no destination set. File with an arrival ICAO.")
            return

        atc_now, stations = is_dest_atc_online(dest, data.get("controllers", []), data.get("atis", []))

        key = (interaction.user.id, callsign.upper())
        self._watchers[key] = WatchEntry(
            user_id=interaction.user.id,
            callsign=callsign.upper(),
            dest_icao=dest,
            created_ts=time.time(),
            notified_now=atc_now,
            active=True
        )

        apt = await self.airports.get(dest)
        apt_name = apt["name"] if apt else dest

        if atc_now:
            lines = "\n".join(stations[:6])
            try:
                await interaction.user.send(
                    f"🟢 **ATC currently online** at **{dest}** ({apt_name}) for `{callsign}`:\n{lines}"
                )
                await interaction.followup.send(
                    f"Watching **{dest}** ({apt_name}). ATC already online — I DM’d you the details.")
            except discord.Forbidden:
                await interaction.followup.send(
                    f"Watching **{dest}** ({apt_name}). ATC is online now, but I couldn't DM you (DMs off).")
        else:
            await interaction.followup.send(f"Watching **{dest}** ({apt_name}). I’ll DM you if ATC comes online.")

    # ----------------- /vatsim_unwatch -----------------
    @app_commands.command(name="vatsim_unwatch", description="Stop watching destination ATC for a callsign.")
    @app_commands.describe(callsign="Your VATSIM callsign")
    async def vatsim_unwatch(self, interaction: discord.Interaction, callsign: str):
        key = (interaction.user.id, callsign.upper())
        entry = self._watchers.get(key)
        if not entry or not entry.active:
            await interaction.response.send_message(f"You're not watching `{callsign}`.", ephemeral=True)
            return
        entry.active = False
        await interaction.response.send_message(f"Stopped watching `{callsign}`.", ephemeral=True)

    # ----------------- background poller -----------------
    @tasks.loop(seconds=60)
    async def poll_vatsim(self):
        if not self._watchers:
            return
        active_items = [(k, e) for k, e in self._watchers.items() if e.active]
        if not active_items:
            return

        try:
            data = await self._get_vatsim_data()
        except Exception:
            return  # transient error

        controllers = data.get("controllers", [])
        atis = data.get("atis", [])

        for (user_id, _cs), entry in active_items:
            atc_now, stations = is_dest_atc_online(entry.dest_icao, controllers, atis)
            if atc_now and not entry.notified_now:
                entry.notified_now = True
                user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                apt = await self.airports.get(entry.dest_icao)
                apt_name = apt["name"] if apt else entry.dest_icao
                lines = "\n".join(stations[:8])
                try:
                    await user.send(
                        f"🟢 **ATC is now online** at **{entry.dest_icao}** ({apt_name}) for `{entry.callsign}`:\n{lines}"
                    )
                except discord.Forbidden:
                    pass

    @poll_vatsim.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(VatsimCog(bot))
