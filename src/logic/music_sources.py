import asyncio
import re
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qs, quote_plus, urlparse

import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

import settings

# Resolving YouTube sources. Everything that talks to yt-dlp or Spotify is
# blocking, so it always runs in a worker thread (asyncio.to_thread) to keep
# the Discord event loop (and the voice heartbeat) responsive.

logger = settings.get_logger()

# YouTube stream URLs expire after ~6h; re-resolve well before that.
STREAM_TTL_SECONDS = 2 * 60 * 60

SPOTIFY_URL_RE = re.compile(
    r'(?:open\.spotify\.com/(?:intl-[a-z]+/)?|spotify:)(track|album|playlist)[/:]([A-Za-z0-9]+)')


class SourceError(Exception):
    """A user-facing error while resolving a song. The message is shown in Discord."""


@dataclass
class Track:
    title: str
    requester: discord.abc.User
    # YouTube (or any yt-dlp supported) page URL. None means "search YouTube
    # for `query` at play time" - used for Spotify tracks so a 500 song
    # playlist doesn't fire 500 YouTube searches up front.
    url: str | None = None
    query: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    _stream_url: str | None = field(default=None, repr=False)
    _resolved_at: float = field(default=0.0, repr=False)
    # YouTube stream URLs answer 403 until a (virtual) pre-roll ad would have
    # finished. yt-dlp reports when that is as `available_at`.
    _available_at: float = field(default=0.0, repr=False)
    user_agent: str | None = field(default=None, repr=False)
    _resolving: asyncio.Future | None = field(default=None, repr=False)

    @property
    def link(self) -> str:
        if self.url:
            return self.url
        return f'https://www.youtube.com/results?search_query={quote_plus(self.query or self.title)}'

    def cached_stream(self) -> str | None:
        if self._stream_url and time.monotonic() - self._resolved_at < STREAM_TTL_SECONDS:
            return self._stream_url
        return None

    def _apply_info(self, info: dict, keep_title: bool = False):
        self.url = info.get('webpage_url') or self.url
        if not keep_title:
            self.title = info.get('title') or self.title
        self.thumbnail = _pick_thumbnail(info) or self.thumbnail
        self.duration = info.get('duration') or self.duration
        if info.get('url'):
            self._stream_url = info['url']
            self._resolved_at = time.monotonic()
            formats = info.get('requested_formats') or [info]
            self._available_at = max(f.get('available_at') or 0 for f in formats)
            self.user_agent = (info.get('http_headers') or {}).get('User-Agent')


class _YtdlLogger:
    """Route yt-dlp output into the bot log instead of stderr."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        logger.warning(f'yt-dlp: {msg}')

    def error(self, msg):
        logger.error(f'yt-dlp: {msg}')


def _ytdl_options(**overrides) -> dict:
    opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': False,
        'skip_download': True,
        'default_search': 'ytsearch',
        # bind to ipv4 since ipv6 addresses cause issues sometimes
        'source_address': '0.0.0.0',
        'logger': _YtdlLogger(),
    }
    # YouTube blocks some (mostly datacenter) IPs with "Sign in to confirm
    # you're not a bot". Exported browser cookies get around that.
    if settings.YTDL_COOKIES_FILE:
        opts['cookiefile'] = settings.YTDL_COOKIES_FILE
    opts.update(overrides)
    return opts


def _extract(target: str, **overrides) -> dict:
    try:
        with YoutubeDL(_ytdl_options(**overrides)) as ydl:
            info = ydl.extract_info(target, download=False)
    except (DownloadError, ExtractorError) as e:
        msg = str(e)
        if 'Sign in' in msg or 'not a bot' in msg:
            raise SourceError('YouTube is blocking the bot (sign-in required). '
                              'Set YTDL_COOKIES_FILE to fix this.') from e
        if 'Private video' in msg or 'Video unavailable' in msg:
            raise SourceError('That video is unavailable or private.') from e
        raise SourceError('Could not read that from YouTube.') from e
    if not info:
        raise SourceError('Nothing found.')
    return info


def _pick_thumbnail(info: dict) -> str | None:
    if info.get('thumbnail'):
        return info['thumbnail']
    thumbs = info.get('thumbnails') or []
    if thumbs:
        return max(thumbs, key=lambda t: (t.get('width') or 0, t.get('height') or 0)).get('url')
    if info.get('ie_key') == 'Youtube' and info.get('id'):
        return f"https://img.youtube.com/vi/{info['id']}/hqdefault.jpg"
    return None


def _is_playlist_url(url: str) -> bool:
    # 'watch?v=...&list=...' plays just the video; a bare list= is a playlist
    query = parse_qs(urlparse(url).query)
    return 'list' in query and 'v' not in query


def _first_entry(info: dict) -> dict:
    if info.get('_type') == 'playlist' or 'entries' in info:
        entries = [e for e in info.get('entries') or [] if e]
        if not entries:
            raise SourceError('Nothing found.')
        return entries[0]
    return info


def _resolve_stream_sync(track: Track) -> str:
    target = track.url or f'ytsearch1:{track.query}'
    info = _first_entry(_extract(target))
    # Keep Spotify's "Title Artist" label; YouTube titles are often noisier
    track._apply_info(info, keep_title=track.url is None)
    if not track._stream_url:
        raise SourceError('No playable audio stream found.')
    return track._stream_url


async def resolve_stream(track: Track) -> str:
    """Return a direct audio stream URL for the track (cached for a while).

    Waits until YouTube actually serves the stream, so this can take a few
    seconds for a freshly resolved track (prefetching hides that).
    """
    url = track.cached_stream()
    if not url:
        # Prefetch and playback can ask at the same time; share one lookup
        if track._resolving is None or track._resolving.done():
            track._resolving = asyncio.ensure_future(asyncio.to_thread(_resolve_stream_sync, track))
        url = await asyncio.shield(track._resolving)
    wait = track._available_at - time.time()
    if wait > 0:
        logger.info(f'Music: waiting {wait:.0f}s for YouTube to release the stream of {track.title!r}')
        await asyncio.sleep(wait)
    return url


# ---------------------------------------------------------------- YouTube --

def _youtube_sync(search: str, requester) -> list[Track]:
    is_url = search.startswith(('http://', 'https://'))

    if is_url and _is_playlist_url(search):
        # Flat extraction only reads the playlist page, not every video
        info = _extract(search, noplaylist=False, extract_flat='in_playlist')
        tracks = []
        for e in info.get('entries') or []:
            if not e or not e.get('url'):
                continue
            tracks.append(Track(title=e.get('title') or e['url'], requester=requester,
                                url=e['url'], thumbnail=_pick_thumbnail(e),
                                duration=e.get('duration')))
        if not tracks:
            raise SourceError('That playlist is empty or private.')
        return tracks

    info = _first_entry(_extract(search if is_url else f'ytsearch1:{search}'))
    track = Track(title=info.get('title') or search, requester=requester)
    track._apply_info(info)
    return [track]


# ---------------------------------------------------------------- Spotify --

_spotify: spotipy.Spotify | None = None


def _spotify_client() -> spotipy.Spotify:
    global _spotify
    if _spotify is None:
        if not (settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET):
            raise SourceError('Spotify is not configured on this bot.')
        _spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET), retries=2)
    return _spotify


def _spotify_query(t: dict) -> str | None:
    if not t or not t.get('name'):
        return None
    artists = ', '.join(a['name'] for a in (t.get('artists') or [])[:2] if a.get('name'))
    return f"{t['name']} - {artists}" if artists else t['name']


def _paginate(sp: spotipy.Spotify, page: dict) -> list[dict]:
    items = list(page.get('items') or [])
    while page.get('next'):
        page = sp.next(page)
        items.extend(page.get('items') or [])
    return items


def _spotify_sync(kind: str, spotify_id: str, requester) -> list[Track]:
    sp = _spotify_client()
    try:
        if kind == 'track':
            raw = [sp.track(spotify_id)]
        elif kind == 'album':
            raw = _paginate(sp, sp.album_tracks(spotify_id, limit=50))
        else:
            page = sp.playlist_items(spotify_id, limit=100, additional_types=('track',),
                                     fields='items(track(name,artists(name),type)),next')
            raw = [it.get('track') for it in _paginate(sp, page)]
    except spotipy.SpotifyException as e:
        if e.http_status == 404 and kind == 'playlist' and spotify_id.startswith('37i9'):
            raise SourceError('Spotify does not let bots read its own curated playlists '
                              '(Daily Mix, This Is..., etc.). Copy it to your own playlist first.') from e
        if e.http_status == 404:
            raise SourceError(f'That Spotify {kind} was not found (is it private?).') from e
        raise SourceError('Spotify request failed.') from e

    tracks = []
    for t in raw:
        if t and t.get('type', 'track') != 'track':
            continue  # podcast episodes
        query = _spotify_query(t)
        if query:
            tracks.append(Track(title=query, requester=requester, query=query))
    if not tracks:
        raise SourceError(f'That Spotify {kind} has no playable tracks.')
    return tracks


# ----------------------------------------------------------------- public --

async def search(text: str, requester) -> list[Track]:
    """Turn whatever the user typed (search text, YouTube URL, Spotify URL) into tracks."""
    text = text.strip().strip('<>')
    spotify = SPOTIFY_URL_RE.search(text)
    try:
        if spotify:
            return await asyncio.to_thread(_spotify_sync, spotify.group(1), spotify.group(2), requester)
        return await asyncio.to_thread(_youtube_sync, text, requester)
    except SourceError:
        raise
    except Exception as e:
        logger.exception(f'Unexpected error resolving {text!r}')
        raise SourceError('Something went wrong looking that up.') from e
