import discord
import datetime
import json
import os
import discord.ext.commands
from discord import app_commands
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import configparser

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True  
client = discord.ext.commands.Bot(command_prefix="/", intents=intents,case_insensitive=True)
MESSAGE_DATA = "message_data.json"
COUNTER_DATA = "counter.json"


def get_token():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config["LOGIN"]["TOKEN"]


def load_data(datafile):
    if os.path.exists(datafile):
        with open(datafile, 'r') as f:
            return json.load(f)
    return {}


def save_message_data(df,datafile):
    df["channel"] = df['channel'].astype(str)
    df = df.fillna("Former Member")
    data = df.to_json(orient="index")
    with open(datafile, 'w') as f:
        json.dump(data, f, indent=4)


def save_counter_data(datafile,counter):
    with open(datafile, 'w') as f:
        json.dump(counter, f, indent=4)


def fix_dataframe(df,username):
    # For certain users there are overlapping months in different years where the number of messages are 0
    # So there are no data points of certain months at all in the dataframe
    # As such these get dropped while grouping and do not get added back when unstacking so we have this workaround here
    # We manually fill those missing data points so that they show up as 0 when unstacking
    missing_months = set([i for i in range(1,13)]) - set(np.unique(df["Month"]))
    if len(missing_months) == 0:
        return df
    for month in missing_months:
        df = pd.concat([pd.DataFrame([[1,2023,month,1,username,0,"general"]], columns=df.columns), df], ignore_index=True)
    return df


def drop_future_months(df):
    # When ungrouping and filling the dataframes, all months of the current year are filled, so future months are filled with 0
    # This just drops the months beyond the current month
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    month_diff = 12 * (current_year - 2023) + current_month
    n_rows = df.shape[0]
    return df.drop([i for i in range(month_diff,n_rows)])


def create_plotting_df(df,individual=False,username=None,channel=None):
    if individual:
        plotting_df = fix_dataframe(df,username).groupby(["Year","Month"]).count().unstack(fill_value=0).stack().reset_index()
    elif channel != None:
        plotting_df = df.groupby(["Year","Month"]).count().unstack(fill_value=0).stack().reset_index()
    else:
        plotting_df = df.groupby(["Year","Month"]).count().unstack(fill_value=0).stack().reset_index()
    plotting_df = drop_future_months(plotting_df)
    return plotting_df


def time_series_plot(df,individual=False,username=None,channel=None):
    df = df[df["Year"] != 2022]
    df = df.drop_duplicates()
    plotting_df = create_plotting_df(df)
    print("---------------")
    print("Displaying the grouped data frame:")
    print(plotting_df)
    print("---------------")
    sns.set_theme()
    plt.clf() # The figure seems to retain its history if this isn't called to clear it
    plot = plt.figure()
    plot = sns.lineplot(x=plotting_df['Month'], y=plotting_df["n_message"], hue=plotting_df['Year'])
    if individual:
        plot.set(ylabel="Number of Messages",title=f"{username}'s message ount")
    elif channel != None:
        plot.set(ylabel="Number of Messages",title=f"{channel}'s message count")
    else:
        plot.set(ylabel="Number of Messages")
    figure = plot.get_figure()
    return figure


def get_last_message_time(df):
    last_message = df[df["id"] == df["id"].max()]
    year = int(last_message["Year"][0])
    month = int(last_message["Month"][0])
    day = int(last_message["Day"][0])
    return datetime.datetime(year,month,day) - datetime.timedelta(1)


async def get_all_messages(full=False):
    message_data = pd.DataFrame(json.loads(load_data(MESSAGE_DATA))).transpose()
    if len(message_data) == 0 or full:
        last_message_time = None
    else:
        last_message_time = get_last_message_time(message_data)
    
    new_data = {"id":[],"Year":[],"Month":[],"Day":[],"Author":[],"n_message":[],"channel":[]}

    for channel in client.get_all_channels():
        if str(channel.type) != 'text':
            continue
        if channel.guild.id != 1043189878210428978:
            continue
        async for message in channel.history(limit=None,after=last_message_time):
            if message.author.bot:
                continue
            id = message.id
            time_created = message.created_at
            author = message.author.name
            new_data["id"].append(id)
            new_data["Author"].append(author)
            new_data["Year"].append(time_created.year)
            new_data["Month"].append(time_created.month)
            new_data["Day"].append(time_created.day)
            new_data["n_message"].append(1)
            new_data["channel"].append(channel)

    new_data = pd.DataFrame(new_data)
    if full:
        df = new_data
        # return new_data
    else:
        df = pd.concat([message_data,new_data])
        df = df.drop_duplicates()
    return df.drop_duplicates()
    # return pd.concat([message_data,new_data]).drop_duplicates()


async def get_all_members():
    members_username = [member.name for member in client.get_all_members()]
    members_global_name = [member.global_name for member in client.get_all_members()]
    return members_username, members_global_name


@client.command(name="resetmsg")
async def reset_message_data(ctx):
    await ctx.send("Rerunning over all messages.")
    message_data = pd.DataFrame(await get_all_messages(full=True))
    save_message_data(message_data,MESSAGE_DATA)
    await ctx.send("Finished rewriting the data.")


@client.command(name="serverstats")
async def time_series_server(ctx):
    await ctx.send("Working on it. Please be patient.")
    df = pd.DataFrame(await get_all_messages())
    df = df.drop_duplicates()
    figure = time_series_plot(df)
    filename = "Server.png"
    figure.savefig(filename)
    image = discord.File(filename)
    save_message_data(df,MESSAGE_DATA)
    await ctx.send(f"Huff Puff! Number crunching is a lot of work!\n",file=image)


@client.command(name="indstats")
async def time_series_individual(ctx,username=None):
    await ctx.send("Working on it. Please be patient.")
    df = pd.DataFrame(await get_all_messages())
    save_message_data(df,MESSAGE_DATA)
    if username == None:
        username = ctx.author.name
    else:
        username = username.lower()
    if username not in np.unique(df["Author"]):
        await ctx.send("No such member found. Better luck next time!")
    else:
        df = df[df["Author"] == username]
        figure = time_series_plot(df,individual=True,username=username)
        filename = "Individual.png"
        figure.savefig(filename)
        image = discord.File(filename)
        await ctx.send(f"Huff Puff! Number crunching is a lot of work!\n.",file=image)


@client.command(name="channelstats")
async def time_series_channel(ctx,channel):
    channel = channel.lower()
    await ctx.send("Working on it. Please be patient.")
    df = pd.DataFrame(await get_all_messages())
    save_message_data(df,MESSAGE_DATA)
    df = df[df["channel"] ==  channel]
    figure = time_series_plot(df,individual=False,channel=channel)
    filename = "Channel.png"
    figure.savefig(filename)
    image = discord.File(filename)
    await ctx.send(f"Huff Puff! Number crunching is a lot of work!\n.",file=image)


@client.command(name="fixcounter")
async def fix_counter(ctx,count,username=None):
    if ctx.author.name not in (username,"f_ms_outlook"):
        await ctx.send("You cannot change someone else's count. You can only change your own count.")
        return
    if username == None:
        username = ctx.author.name
    counter[username] = int(count)
    save_counter_data(COUNTER_DATA,counter)
    await ctx.send(f"Counter fixed!")


@client.command(name="showcounter")
async def show_counter(ctx,*usernames):
    if len(usernames) == 0:
        username = ctx.author.name
        await ctx.send(f"You have sent {counter[username]} messages!")
    else:
        for username in usernames:
            username = username.lower()
            await ctx.send(f"{username} has sent {counter[username]} messages!")


@client.command(name="info")
async def help(ctx,command_name=None):
    if command_name != None:
        command_name = command_name.lower()

    if command_name == None:
        message = """Hello! This is a simple bot that keeps track of the number of messages posted in this server.
Use / as a prefix to send a command. Commands are entirely **case insensitive**. The available commands are as follows:

* serverstats
* indstats
* channelstats
* fixcounter
* showcounter
* resetmsg

To find out more about these commands you can type /info 'command'.
            
Found a bug? Oops!"""
        
    elif command_name == "serverstats":
        message = """A command to plot the message frequency of this server between 2023 and the current time.
        
**Usage**: 
/serverstats"""
        
    elif command_name == "indstats":
        message = """A command to plot the message frequency of a discord user between 2023 and the current time.
        
**Usage**: 
/indstats username
            
**Options**: 
username (*optional*) - discord username (the thing that originally had a 4 digit number)"""

    elif command_name == "channelstats":
        message = """A command to plot the message frequency of a channel between 2023 and the current time.
        
**Usage**: 
/channelstats channel
            
**Options**: 
channel - discord channel"""
        
    elif command_name == "showcounter":
        message = """A command to show the message count of discord user(s). Note that some deleted messages may be tracked. See fixcounter to solve.
        
**Usage**: 
/showcounter usernames
            
**Options**: 
usernames (*required*) - discord usernames (the thing that originally had a 4 digit number); must be separated by a space"""
        
    elif command_name == "fixcounter":
        message = """A command to assign a different message count to a discord user.
        
**Usage**: 
/fixcounter count username

**Options**: 
count (*required*) - the new message count 
username (*optional*) - discord username (the thing that originally had a 4 digit number)"""
    
    elif command_name == "info":
        message = """Haha very funny. The command is self explanatory. If you cannot figure it out then too bad."""

    elif command_name == "resetmsg":
        message = """A command to reset and recompute the message data. **WARNING**: This will take a lot of time.
    
**Usage**:
/resetmsg"""

    else:
        message = """I do not understand what you mean. I am afraid I cannot help you. Please try again."""
        
    await ctx.send(message)


@client.event
async def on_ready():
    pass


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    # Future proofed if a new member joins?
    if message.author.name not in counter.keys():
        counter[message.author.name] = 0
    counter[message.author.name] += 1
    await client.process_commands(message)
    if counter[message.author.name] % 100000 == 0:
        await message.channel.send(f"Wow {message.author.mention}! Who would have thought you'd hit {counter[message.author.name]} messages?")
    elif counter[message.author.name] % 10000 == 0:
        if counter[message.author.name] != 10000:
            await message.channel.send(f"Hey {message.author.mention} you're on fire! That's another 10000 messages!")
        else: 
            await message.channel.send(f"Welcome to the 10k club {message.author.mention}!")
    elif counter[message.author.name] % 1000 == 0:
        await message.channel.send(f"Hey {message.author.mention}. Looks like another 1000 messages. Nice?!?")
        
    # Save reasonably frequently
    if counter[message.author.name] % 100 == 0:
        save_counter_data(COUNTER_DATA,counter)


@client.event
async def on_message_delete(message):
    if message.author == client.user:
        return
    counter[message.author.name] -= 1
    save_counter_data(COUNTER_DATA,counter)


counter = load_data(COUNTER_DATA)
TOKEN = get_token()
client.run(TOKEN)
