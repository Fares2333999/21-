from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import datetime
import asyncio
import json

# نظام سيرفر الويب لكي يبقى البوت متصلاً (24/7)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        TOKEN = config.get("TOKEN", "")
except FileNotFoundError:
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="", intents=intents, help_command=None)

ADMIN_ROLE_ID = 1505552959449337897
IMAGE_SENDER_ROLE_ID = 1506003494975312024

AUTO_JOIN_VOICE_CHANNEL_ID = 1505998430068281415
IMAGE_SYSTEM_CHANNEL_ID = 1505999827824021614
GAME_ROLES_CHANNEL_ID = 1505998099095486646
REQUEST_PLAYERS_CHANNEL_ID = 1505997745058611220
REQUEST_PING_CHANNEL_ID = 1505997764855857243

IMAGE_TARGETS = {
    "avt": 1505994569525887167,
    "profile": 1505994624672465109,
    "avt-g": 1505994660445687939,
    "banner": 1505994686882512916
}

GAMES = {
    "Counter Strike 2": {"role": 1505997854387208264, "voice": [1505931964425830457]},
    "Valorant": {"role": 1505997924625285263, "voice": [1505928407924342846]},
    "Fortnite": {"role": 1505997952584515684, "voice": [1505928717061324831, 1505928931432202271]},
    "League Of Legends": {"role": 1505997983924097205, "voice": [1505932152989024358]},
    "Rocket League": {"role": 1506002399536484493, "voice": [1505947224369266728]}
}

def has_admin_role():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator: return True
        return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)

class AskView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ask", style=discord.ButtonStyle.primary, custom_id="persistent_ask_btn")
    async def ask_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message.embeds:
            return await interaction.response.send_message("لم يتم العثور على صورة.", ephemeral=True)
         
        image_url = interaction.message.embeds[0].image.url
        if not image_url:
             return await interaction.response.send_message("لم يتم العثور على صورة.", ephemeral=True)
             
        try:
            embed = discord.Embed()
            embed.set_image(url=image_url)
            await interaction.user.send("تفضل الصورة:", embed=embed)
            await interaction.response.send_message("تم إرسال الصورة في الخاص.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("الخاص لديك مغلق، يرجى فتحه أولاً.", ephemeral=True)

class GameRoleSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=game, value=game) for game in GAMES.keys()]
        super().__init__(placeholder="اختار لعبتك...", min_values=1, max_values=1, options=options, custom_id="persistent_game_role_select")

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]
        role_id = GAMES[game_name]["role"]
        role = interaction.guild.get_role(role_id)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"تم إزالة رول {game_name} منك.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"تم إعطاؤك رول {game_name}.", ephemeral=True)

class GameRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GameRoleSelect())

class RequestSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=game, value=game) for game in GAMES.keys()]
        super().__init__(placeholder="اختر اللعبة...", min_values=1, max_values=1, options=options, custom_id="persistent_request_select")

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]
        expected_voice_ids = GAMES[game_name]["voice"]
        role_id = GAMES[game_name]["role"]
        
        user_voice = interaction.user.voice
        if not user_voice or not user_voice.channel or user_voice.channel.id not in expected_voice_ids:
            return await interaction.response.send_message(f"ادخل الروم الصوتية الخاصة بـ {game_name} قبل الطلب", ephemeral=True)
            
        ping_channel = interaction.guild.get_channel(REQUEST_PING_CHANNEL_ID)
        role = interaction.guild.get_role(role_id)
        invite_link = f"https://discord.com/channels/{interaction.guild.id}/{user_voice.channel.id}"
        
        await ping_channel.send(f"طلب لاعبين من {interaction.user.mention}\nاللعبة: {role.mention}\nالروم الصوتي: {invite_link}")
        await interaction.response.send_message("تم إرسال طلب اللاعبين بنجاح!", ephemeral=True)

class RequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RequestSelect())

@bot.event
async def on_ready():
    bot.add_view(AskView())
    bot.add_view(GameRoleView())
    bot.add_view(RequestView())
    
    game_channel = bot.get_channel(GAME_ROLES_CHANNEL_ID)
    if game_channel:
        try:
            await game_channel.purge(limit=10)
            await game_channel.send("رولات الألعاب - اختار لعبتك", view=GameRoleView())
        except Exception:
            pass

    req_channel = bot.get_channel(REQUEST_PLAYERS_CHANNEL_ID)
    if req_channel:
        try:
            await req_channel.purge(limit=10)
            await req_channel.send("طلب لاعبين", view=RequestView())
        except Exception:
            pass
    
    channel = bot.get_channel(AUTO_JOIN_VOICE_CHANNEL_ID)
    if channel and isinstance(channel, discord.VoiceChannel):
        try:
            if not channel.guild.voice_client:
                vc = await channel.connect()
        except Exception:
            pass
        
        try:
            await channel.guild.change_voice_state(channel=channel, self_deaf=True)
        except Exception:
            pass

@bot.event
async def on_message(message):
    if message.author.bot: return

    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.process_commands(message)
        return

    if message.content.startswith('!'):
        if message.channel.id != IMAGE_SYSTEM_CHANNEL_ID: return
        is_admin = False
        if isinstance(message.author, discord.Member):
            is_admin = message.author.guild_permissions.administrator or any(role.id == ADMIN_ROLE_ID for role in message.author.roles)
        
        if is_admin:
            text = message.content[1:].strip()
            if text:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                await message.channel.send(text)

@bot.command(name="برا")
@has_admin_role()
async def ban_user(ctx, member: discord.Member):
    await member.ban(reason=f"Banned by {ctx.author}")
    await ctx.send(f"تم تبنيد {member.mention}")

@bot.command(name="سحب")
@has_admin_role()
async def move_user(ctx, member: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("يجب أن تكون في روم صوتي لسحب العضو.")
    if not member.voice or not member.voice.channel:
        return await ctx.send("العضو ليس في روم صوتي.")
    await member.move_to(ctx.author.voice.channel)
    await ctx.send(f"تم سحب {member.mention} إلى الروم الخاص بك.")

@bot.command(name="رول")
@has_admin_role()
async def give_role(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"تم إعطاء الرتبة {role.name} للعضو {member.mention}")

@bot.command(name="صورة")
@has_admin_role()
async def get_avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.display_avatar.url)

class TimeoutSelect(discord.ui.Select):
    def __init__(self, target_member: discord.Member):
        self.target_member = target_member
        options = [
            discord.SelectOption(label="دقيقة", value="1"),
            discord.SelectOption(label="نصف ساعة", value="30"),
            discord.SelectOption(label="ساعة", value="60"),
            discord.SelectOption(label="ساعة ونصف", value="90"),
            discord.SelectOption(label="ساعتين", value="120"),
            discord.SelectOption(label="ثلاثة ساعات", value="180"),
            discord.SelectOption(label="24 ساعة", value="1440"),
            discord.SelectOption(label="168 ساعة", value="10080"),
        ]
        super().__init__(placeholder="اختر مدة التايم أوت...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
        
        duration_minutes = int(self.values[0])
        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration_minutes)
        await self.target_member.timeout(until, reason=f"Timeout by {interaction.user}")
        await interaction.response.send_message(f"تم إعطاء تايم أوت لـ {self.target_member.mention} لمدة {duration_minutes} دقيقة.", ephemeral=False)
        self.disabled = True
        await interaction.message.edit(view=self.view)

class TimeoutView(discord.ui.View):
    def __init__(self, target_member: discord.Member):
        super().__init__(timeout=120)
        self.add_item(TimeoutSelect(target_member))

@bot.command(name="تايم")
@has_admin_role()
async def timeout_user(ctx, member: discord.Member):
    view = TimeoutView(member)
    await ctx.send(f"اختر مدة التايم أوت للعضو {member.mention}:", view=view)

class ImageChannelSelect(discord.ui.Select):
    def __init__(self, image_url: str):
        self.image_url = image_url
        options = [
            discord.SelectOption(label="avt", value="avt"),
            discord.SelectOption(label="profile", value="profile"),
            discord.SelectOption(label="avt-g", value="avt-g"),
            discord.SelectOption(label="banner", value="banner"),
        ]
        super().__init__(placeholder="اختر الروم لإرسال الصورة...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        target_channel_id = IMAGE_TARGETS[self.values[0]]
        target_channel = interaction.guild.get_channel(target_channel_id)
        
        embed = discord.Embed()
        embed.set_image(url=self.image_url)
        
        view = AskView()
        await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"تم إرسال الصورة بنجاح إلى {target_channel.mention}", ephemeral=True)
        self.disabled = True
        await interaction.message.edit(view=self.view)

class ImageSelectView(discord.ui.View):
    def __init__(self, image_url: str):
        super().__init__(timeout=300)
        self.add_item(ImageChannelSelect(image_url))

@bot.command(name="رسالة", aliases=["ارسال"])
async def send_image(ctx):
    if ctx.channel.id != IMAGE_SYSTEM_CHANNEL_ID: return
    if not any(role.id == IMAGE_SENDER_ROLE_ID for role in ctx.author.roles) and not ctx.author.guild_permissions.administrator:
        return await ctx.send("ليس لديك صلاحية لإرسال الصور.")
        
    await ctx.send("الرجاء إرسال الصورة الآن (لديك 60 ثانية).")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.attachments
        
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        image_url = msg.attachments[0].url
        view = ImageSelectView(image_url)
        await ctx.send("عايز تبعتها ف انهي روم ؟", view=view)
    except asyncio.TimeoutError:
        await ctx.send("انتهى الوقت، لم تقم بإرسال صورة.")

@bot.command(name="setup_roles")
@has_admin_role()
async def setup_roles_cmd(ctx):
    view = GameRoleView()
    await ctx.send("رولات الألعاب - اختار لعبتك", view=view)

@bot.command(name="setup_requests")
@has_admin_role()
async def setup_requests_cmd(ctx):
    view = RequestView()
    await ctx.send("طلب لاعبين", view=view)

if __name__ == "__main__":
    keep_alive()  # تشغيل السيرفر ليعمل البوت على الويب بشكل دائم
    if TOKEN and TOKEN != "ضع_توكن_البوت_هنا_YOUR_BOT_TOKEN_HERE":
        bot.run(TOKEN)