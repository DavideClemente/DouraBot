from interactions import slash_command, slash_option, SlashContext, OptionType, Button, ButtonStyle,  ComponentContext, component_callback


async def teste(ctx: SlashContext, integer_option: int):
    await ctx.send(f'Your input: {integer_option}')


async def test_button(ctx: SlashContext):
    components = Button(
        custom_id="button_1",
        style=ButtonStyle.BLUE,
        label="Click me"
    )
    await ctx.send("Buttons test", components=components)
