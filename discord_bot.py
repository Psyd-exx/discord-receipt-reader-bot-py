import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import pytesseract
import cv2
import numpy as np
import re
import pandas as pd

intents = discord.Intents.default()
intents.message_content = True

load_dotenv()
token = os.getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='$', intents=intents)

@bot.command(name='hello')
async def say_hello(ctx):
    await ctx.send('Hello!')

@bot.command(name='receipt')
async def say_hello(ctx):
    channel = ctx.channel
    thread = await channel.create_thread(name='Receipts Thread')
    await thread.send('Welcome to the Receipts thread!')
    await thread.send('Please send your images here!')

@bot.command(name='scan')
async def scan_receipt(ctx, *names):
    message = ctx.message
    df = pd.DataFrame(columns=["Names", "Costs"])

    if len(message.attachments) == 0:
        await ctx.send("Please attach at least one valid image type when using the `$scan` command.")
        return

    if len(names) != len(message.attachments):
        await ctx.send("Please provide a name for each image attached.")
        return

    image_order = 1

    for i, (image, name) in enumerate(zip(message.attachments, names)):

        if image.filename.lower().endswith(('.png', '.jpg', '.jpeg')) == False:
            await ctx.send("Please attach a valid image file. ")
            continue

        response = await image.read()
        nparr = np.frombuffer(response, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        text = pytesseract.image_to_string(gray)
        total = extract_total(text)

        print("Total:",total)

        if total == 0:
            df = pd.concat([df, pd.DataFrame({"Costs": [0], "Names": [name.replace(",", "")]}, index=[i])], ignore_index=True)
        else:
            df = pd.concat([df, pd.DataFrame({"Costs": [total], "Names": [name.replace(",", "")]}, index=[i])], ignore_index=True)

        if len(message.attachments) > 1:
            await ctx.send(f"Image {image_order} scanned!")
        else:
            await ctx.send("Image scanned!")
            
        image_order += 1

    # finding the sum of the costs column and adding it to the bottom of the csv file
    total_cost = df["Costs"].sum()
    df.loc[df.index.max() + 2, "Costs"] = "Total Cost: " + str(float(total_cost))

    df.to_csv("receipt_cost.csv", index=False)

    try:
        with open('receipt_cost.csv', 'rb') as f:
            file = discord.File(f, filename='receipt_cost.csv')
            await ctx.send(file=file)
    except FileNotFoundError:
        await ctx.send("CSV file not be found!")

def extract_total(text):
    lines = text.split('\n')
    total = 0
    for line in lines:
        if re.search("otal", line.lower()):
            try:
                joinedLine = "".join(line.split())
                total = float(joinedLine[-5:])
                break
            except:
                try:
                    joinedLine = "".join(line.split())
                    total = float(joinedLine[-4:])
                    break
                except:
                    print("Could not find a total price!")
    return total

bot.run(token)