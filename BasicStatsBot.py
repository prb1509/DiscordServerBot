import discord
from datetime import datetime
import json
import os
import discord.ext.commands
from discord import app_commands
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True  
client = discord.ext.commands.Bot(command_prefix="/", intents=intents)
DATA = "message_data.json"

def load_message_data():
    # return{}
    if os.path.exists(DATA):
        with open(DATA, 'r') as f:
            return json.load(f)
    return {}

def save_message_data(df):
    df["channel"] = df['channel'].astype(str)
    df = df.fillna("Former Member")
    data = df.to_json(orient="index")
    with open(DATA, 'w') as f:
        json.dump(data, f, indent=4)

def time_series_plot(df,individual=False,username=None):
    df = df[df["Year"] != 2022]
    plotting_df = df.groupby(["Year","Month"]).sum().reset_index()
    sns.set_theme()
    print(plotting_df)
    plt.clf()
    plot = plt.figure()
    plot = sns.lineplot(x=plotting_df['Month'], y=plotting_df["n_message"], hue=plotting_df['Year'])
    if individual:
        plot.set(ylabel="Number of Messages",title=f"{username}'s Message Count")
    else:
        plot.set(ylabel="Number of Messages")
    figure = plot.get_figure()
    return figure

@client.command(name="serverstats")
async def time_series_server(ctx):
    now = datetime.now()
    df = pd.DataFrame(await get_all_messages())
    figure = time_series_plot(df)
    filename = "Server.png"
    figure.savefig(filename)
    image = discord.File(filename)
    save_message_data(df)
    dt = datetime.now() - now
    await ctx.send(f"Huff Puff! Number crunching is a lot of work!\n This took {dt.total_seconds()} seconds because Latio is a bad programmer.",file=image)

@client.command(name="indstats")
async def time_series_individual(ctx,username):
    members_username, members_global_name = await get_all_members()
    if username not in members_global_name and username not in members_username:
        await ctx.send("No such member found. Better luck next time!")
        # await ctx.send("The members are:")
        # for i in range(len(members_username)):
        #     await ctx.send(f"{members_username[i]}\n {members_global_name[i]}\n")
    else:
        now = datetime.now()
        df = pd.DataFrame(await get_all_messages())
        # save_message_data(df)
        print(np.unique(df["Author"]))
        try:
            df = df[df["Author"] == username]
        except KeyError:
            await ctx.send("Name found, but the code does not work yet for it. ")
        figure = time_series_plot(df)
        filename = "Individual.png"
        figure.savefig(filename)
        image = discord.File(filename)
        dt = datetime.now() - now
        await ctx.send(f"Huff Puff! Number crunching is a lot of work!\n This took {dt.total_seconds()} seconds because Latio is a bad programmer.",file=image)

@client.event
async def on_ready():
    # await get_all_messages()
    pass

async def get_all_messages():
    message_data = pd.DataFrame(json.loads(load_message_data())).transpose()
    if len(message_data) != 0 :
        return message_data
    
    # new_data = {"id":[],"UTC":[],"Year":[],"Month":[],"Day":[],"Author":[],"n_message":[],"channel":[]}
    new_data = {"id":[],"Year":[],"Month":[],"Day":[],"Author":[],"n_message":[],"channel":[]}

    for channel in client.get_all_channels():
        if str(channel.type) != 'text':
            continue
        if channel.guild.id !=1043189878210428978:
            continue
        async for message in channel.history(limit=None):
            if message.author.bot:
                continue
            id = message.id
            time_created = message.created_at
            if time_created.year in (2025,2022): 
                continue
            author = message.author.name
            new_data["id"].append(id)
            new_data["Author"].append(author)
            # new_data["UTC"].append(time_created)
            new_data["Year"].append(time_created.year)
            new_data["Month"].append(time_created.month)
            new_data["Day"].append(time_created.day)
            new_data["n_message"].append(1)
            new_data["channel"].append(channel)

    #this is obviously incorrect since message_data is not empty and the two objects need to be combined correctly
    return new_data

async def get_all_members():
    members_username = [member.name for member in client.get_all_members()]
    members_global_name = [member.global_name for member in client.get_all_members()]
    return members_username, members_global_name

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    await client.process_commands(message)

#no one is actually stealing this idgaf
client.run("MTMzNDMxMzk2NjkyNjU2NTQ1OA.GZdgpc.TIPQLMUlRklq2OCy5S49iHyvCrVx-vO-1FnNvw")