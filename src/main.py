from calendar import weekday
import copy
from datetime import datetime, timezone
from email import message
import enum
import json
import logging
from operator import index
from os import kill
import os
import random
from sqlite3 import Time
from subprocess import call
from tabnanny import check
import time
from tracemalloc import BaseFilter
from xml.etree.ElementPath import get_parent_map
from click import get_current_context
from numpy import broadcast, full
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from env import get_api_key, get_port
from telebot import types, telebot
from telegram import CallbackQuery, ParseMode
import ast
from dbhelper import DBHelper, DBKeysMap, factionDataKeys, playerDataKeys
import pandas
import atexit
from twisted.internet import task, reactor
from listDict import ListDict
from prize import Prize

PORT = get_port()
API_KEY = get_api_key()
if API_KEY == None:
    raise Exception("Please update API Key")

#==========================Logging===========================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Initialise bot
bot = telebot.TeleBot(API_KEY, parse_mode=None)

# ============================Constants======================================

# TODO: UPDATE
admins = ["praveeeenk", "Casperplz", "Jobeet"]
numOfPrizes = 5
numBlanksToAddUponPlay = numOfPrizes // 2
availablePrizes = ListDict()
for i in range(1, numOfPrizes + 1):
    #TODO: Change to Actual Names, load from EXCEL
    newPrize = Prize(i, f"Prize Name {i}")
    availablePrizes.add_item(newPrize)


# =============================Texts==========================================
dontWasteMyTimeText = """\"Don't waste my time...You aren't allowed to use this command now.\"
~ Message by Caserplz"""

# ======================LOAD GAME STATE================================
# Load Database
mainDb = DBHelper("oldHCEvent.sqlite")
# Clear DB first, then setup
# mainDb.purgeData()
# mainDb.setup()
# mainDb.playerDataJSONArrToDB(playerDataRound1JSONArr, 1)
# mainDb.playerDataJSONArrToDB(playerDataRound2JSONArr, 2)
# mainDb.factionDataJSONArrToDB(factionDataJSONArr)

playerTracker = {}

# ============================Key boards===================================
# Makes Inline Keyboard

def makeInlineKeyboard(lst, optionID):
    markup = types.InlineKeyboardMarkup()
    for value in lst:
        markup.add(types.InlineKeyboardButton(text=value,
                                              callback_data=f"['optionID', '{optionID}', 'value', '{value}']"))
    return markup

# ============================DB to file converters?===========================

# def saveGameState():
#     db = DBHelper("shan-royale.sqlite")
#     currentTime = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
#     print(f"SAVING GAME STATE AT: {currentTime}")
#     allPlayerData1Dict = db.getALLPlayerDataJSON(1)
#     allPlayerData2Dict = db.getALLPlayerDataJSON(2)
#     allFactionDataDict = db.getALLFactionDataJSON()
    
#     gameDataDict = {}
#     dummyDict = {}
#     for key in gameDataKeys.allKeys:
#         dummyDict[key] = getattr(currentGame, key)
#     gameDataDict["game"] = dummyDict

#     dummyTrackerDict = {}
#     for username, dictionary in userTracker.items():
#         temp = {}
#         temp[userTrackerDataKeys.username] = username
#         for key, value in dictionary.items():
#             temp[key] = value
#         dummyTrackerDict[username] = temp

#     dummyAdminDict = {}
#     for username, dictionary in adminQuery.items():
#         temp = {}
#         for state, text in dictionary.items():
#             temp[adminQueryDataKeys.username] = username
#             temp[adminQueryDataKeys.state] = state
#             temp[adminQueryDataKeys.text] = text
#         dummyAdminDict[username] = temp

#     allPlayerData1JSON = pandas.DataFrame.from_dict(allPlayerData1Dict, orient="index")
#     allPlayerData2JSON = pandas.DataFrame.from_dict(allPlayerData2Dict, orient="index")
#     allFactionDataJSON = pandas.DataFrame.from_dict(allFactionDataDict, orient="index")
#     gameDataJSON = pandas.DataFrame.from_dict(gameDataDict, orient="index")
#     userTrackerJSON = pandas.DataFrame.from_dict(dummyTrackerDict, orient="index")
#     adminQueryJSON = pandas.DataFrame.from_dict(dummyAdminDict, orient="index")

#     # Save to backup sheet
#     saveBackupFilePath = f"./excel/backup/shanRoyale2022-{currentTime}.xlsx"
#     with pandas.ExcelWriter(saveBackupFilePath) as writer:
#         allPlayerData1JSON.to_excel(writer, sheet_name=SheetName.playerDataRound1)
#         allPlayerData2JSON.to_excel(writer, sheet_name=SheetName.playerDataRound2)
#         allFactionDataJSON.to_excel(writer, sheet_name=SheetName.factionData)
#         gameDataJSON.to_excel(writer, sheet_name=SheetName.gameData)
#         userTrackerJSON.to_excel(writer, sheet_name=SheetName.userTrackerData)
#         adminQueryJSON.to_excel(writer, sheet_name=SheetName.adminQueryData)

#     # Save to live excel sheet too
#     with pandas.ExcelWriter(liveExcelFilePath) as writer:
#         allPlayerData1JSON.to_excel(writer, sheet_name=SheetName.playerDataRound1)
#         allPlayerData2JSON.to_excel(writer, sheet_name=SheetName.playerDataRound2)
#         allFactionDataJSON.to_excel(writer, sheet_name=SheetName.factionData)
#         gameDataJSON.to_excel(writer, sheet_name=SheetName.gameData)
#         userTrackerJSON.to_excel(writer, sheet_name=SheetName.userTrackerData)
#         adminQueryJSON.to_excel(writer, sheet_name=SheetName.adminQueryData)

#     print(f"DONE SAVING GAME STATE")

# ====================Other helpers=========================

def blastMessageToAll(text):
    for user in playerTracker.values():
        bot.send_message(chat_id= user["chat_id"],
                         text = text,
                         parse_mode = 'HTML')

def blastImageToAll(path):
    for user in playerTracker.values():
        bot.send_photo(chat_id= user["chat_id"],
                         photo=open(path, 'rb'))

# ===================Command Method============================
def startCmd(update, context):
    username = update.message.chat.username
    chat_id = update.message.chat.id
    if username in playerTracker:
        bot.send_message(chat_id=chat_id,
            text="You are already registered!\n\n" + dontWasteMyTimeText)
        return
    newPlayer = {
        "numBlanks": 0,
        "prize": None
    }
    playerTracker[username] = newPlayer
    bot.send_message(chat_id=chat_id, text="Thanks for registering!")

def dipCmd(update, context):
    text_array = update.message.text.split()
    chat_id = update.message.chat.id
    if len(text_array) != 2:
        bot.send_message(chat_id=chat_id,
            text="Please enter the command with this format!\n\n/dip USERNAME\n\nMake sure you remove the @ before typing in the username")
        return

    adminUsername = update.message.chat.username
    playerUsername = text_array[1]
    if adminUsername not in admins:
        bot.send_message(chat_id=chat_id,
            text="Only admins can use this command!\n\n" + dontWasteMyTimeText)
        return
    if playerUsername not in playerTracker:
        bot.send_message(chat_id=chat_id,
            text="Player hasn't registered yet :(\n\nDid you type in the correct username?\n\nMake sure you remove the @ before typing in the username")
        return
    
    player = playerTracker[playerUsername]
    drawnPrize = availablePrizes.choose_random_item()
    numPrizesAndBlanks = availablePrizes.size() + player["numBlanks"]
    player["numBlanks"] += numBlanksToAddUponPlay

    # See if player drew blank
    selectedID = random.randint(1, numPrizesAndBlanks)
    print(f"SelectedID: {selectedID}, availablePrizes Size: {availablePrizes.size()}")
    if selectedID > availablePrizes.size(): 
        currentPrize = player["prize"]
        bot.send_message(chat_id=chat_id, text=f"Player draw a blank!\n\nTheir prize does not change, so their current prize will still be '{currentPrize.name}' (Prize ID {currentPrize.id})")
        return

    # If player didnt draw blank
    availablePrizes.remove_item(drawnPrize)
    drawnPrize.heldBy = adminUsername
    if player["prize"]:
        # Swap prizes
        removedPrize = player["prize"]
        availablePrizes.add_item(removedPrize)
        removedPrize.heldBy = None
    player["prize"] = drawnPrize
    bot.send_message(chat_id=chat_id, text=f"Player now has '{drawnPrize.name}' (Prize ID {drawnPrize.id})")
    print(playerTracker)

def peekPlayerCmd(update, context):
    text_array = update.message.text.split()
    chat_id = update.message.chat.id
    if len(text_array) != 2:
        bot.send_message(chat_id=chat_id,
            text="Please enter the command with this format!\n\n/peekPlayer USERNAME\n\nMake sure you remove the @ before typing in the username")
        return

    adminUsername = update.message.chat.username
    playerUsername = text_array[1]
    if adminUsername not in admins:
        bot.send_message(chat_id=chat_id,
            text="Only admins can use this command!\n\n" + dontWasteMyTimeText)
        return
    if playerUsername not in playerTracker:
        bot.send_message(chat_id=chat_id,
            text="Player hasn't registered yet :(\n\nDid you type in the correct username?\n\nMake sure you remove the @ before typing in the username")
        return
    prize = playerTracker[playerUsername]["prize"]
    if prize == 0:
        bot.send_message(chat_id=chat_id, text=f"Player hasn't won a prize yet!")
        return
    bot.send_message(chat_id=chat_id, text=f"Player now has '{prize.name}' (Prize ID {prize.id})")
    print(playerTracker)

def printAvailablePrizes(chat_id):
    fullText = "Available Prizes:\n\n"
    copyOfAvailablePrizes = copy.deepcopy(availablePrizes.items)
    copyOfAvailablePrizes.sort(key=lambda prize: prize.id)
    for prize in copyOfAvailablePrizes:
        fullText += f"{prize.name} (ID. {prize.id}) (Held by: {prize.heldBy})\n"
    fullText += f"\nTotal Number of Available Prizes: {availablePrizes.size()}"
    bot.send_message(chat_id=chat_id, text=fullText)

def printTakenPrizes(chat_id):
    fullText = "Taken Prizes:\n\n"
    i = 0
    for data in playerTracker.values():
        prize = data["prize"]
        if not prize:
            continue
        fullText += f"{prize.name} (ID. {prize.id}) (Held by: {prize.heldBy})\n"
        i += 1
    if i == 0:
        fullText += "No prizes have been taken yet!"
    else:
        fullText += f"\nTotal Number of Taken Prizes: {i}"
    bot.send_message(chat_id=chat_id, text=fullText)

def peekPrizesCmd(update, context):
    username = update.message.chat.username
    chat_id = update.message.chat.id
    if username not in playerTracker:
        bot.send_message(chat_id=chat_id,
            text="Player hasn't registered yet :(\n\nPress /start")
        return
    printAvailablePrizes(chat_id=chat_id)
    printTakenPrizes(chat_id=chat_id)
    print(playerTracker)

# ===================Main Method============================

def main():

    # Start the bot.
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(API_KEY, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Game Master commands
    dp.add_handler(CommandHandler("dip", dipCmd))
    dp.add_handler(CommandHandler("peekPlayer", peekPlayerCmd))

    # All commands
    dp.add_handler(CommandHandler("start", startCmd))
    dp.add_handler(CommandHandler("peekPrizes", peekPrizesCmd))

    
    # Save Game State upon exit
    # atexit.register(saveGameState)
 
    # Start the Bot
    # updater.start_webhook(listen="0.0.0.0",
    #                   port=int(PORT),
    #                   url_path=str(API_KEY),
    #                   webhook_url='https://radiant-inlet-41935.herokuapp.com/' + str(API_KEY))

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.start_polling()

    # Save Excel sheet every 90s
    # timeout = 60
    # l = task.LoopingCall(saveGameState)
    # l.start(timeout)
    # reactor.run()


if __name__ == '__main__':
    main()
