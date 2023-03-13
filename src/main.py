from twisted.internet import task, reactor
import copy
import json
import logging
import random
from telegram.ext import Updater, CommandHandler
from env import get_api_key, get_port
from telebot import types, telebot
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

admins = ["praveeeenk", "Casperplz", "Jobeet", "vigonometry", "kelsykoh", "kelsomebody"]
# allPrizes = ListDict()
availablePrizes = ListDict()
playerTracker = {}


# =============================Texts==========================================
dontWasteMyTimeText = """\"Don't waste my time...You aren't allowed to use this command now.\"
~ Message by Caserplz"""

# ======================Storage Functions================================
def loadGameState():
    global playerTracker
    with open('data.json', 'r') as prizes_file:
        prizes_data = json.load(prizes_file)
    
    for prize in prizes_data["prizes"]:
        newPrize = Prize(prize["id"], prize["name"])
        if prize["heldBy"]:
            newPrize.heldBy = prize["heldBy"]
        # allPrizes.add_item(newPrize)
        availablePrizes.add_item(newPrize)
    
    for username, tracker in prizes_data["playerTracker"].items():
        player_object = {
            "prize": None
        }
        if tracker["prize"]:
            json_prize_object = tracker["prize"]
            player_prize = Prize(json_prize_object["id"], json_prize_object["name"])
            player_prize.heldBy = username
            player_object["prize"] = player_prize
        playerTracker[username] = player_object
    
    logger.info("Loaded Game State---------------------------------------------------------------")
    for username, tracker in playerTracker.items():
        prize_string = "null"
        if tracker["prize"]:
            prize_string = str(tracker["prize"].toJSON())
        logger.info(username + ": " + prize_string)
    
    for prize in availablePrizes.items:
        heldBy = prize.heldBy
        if not heldBy:
            heldBy = "null"
        logger.info(str(prize.id) + ", " + prize.name + ", " + heldBy)

def saveGameState():
    storage_json_object = {}
    player_tracker_json_object = {}
    for key, value in playerTracker.items():
        player_json_object = {
            "prize": None
        }
        if value["prize"]:
            player_json_object["prize"] = value["prize"].toJSON()
        player_tracker_json_object[key] = player_json_object
    storage_json_object["playerTracker"] = player_tracker_json_object
    
    prizes_array = []
    for prize in availablePrizes.items:
        prizes_array.append(prize.toJSON())
    storage_json_object["prizes"] = prizes_array
    with open('data.json', 'w') as prizes_file:
        json.dump(storage_json_object, prizes_file)

    logger.info("Stored Game State---------------------------------------------------------------")
    logger.info(storage_json_object)


# ============================Key boards===================================
# Makes Inline Keyboard

def makeInlineKeyboard(lst, optionID):
    markup = types.InlineKeyboardMarkup()
    for value in lst:
        markup.add(types.InlineKeyboardButton(text=value,
                                              callback_data=f"['optionID', '{optionID}', 'value', '{value}']"))
    return markup

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
    numPrizesAndBlanks = availablePrizes.size() * 2

    # See if player is already holding onto a prize
    if player["prize"]:
        # See if player drew blank
        selectedID = random.randint(1, numPrizesAndBlanks)
        print(f"SelectedID: {selectedID}, availablePrizes Size: {availablePrizes.size()}")
        if selectedID > availablePrizes.size():
            removedPrize = player["prize"]
            availablePrizes.add_item(removedPrize)
            removedPrize.heldBy = None
            player["prize"] = None
            bot.send_message(chat_id=chat_id, text=f"Player draw a blank!\n\nYou lost your prize ;(")
            return
        
        # If not blank, remove their current prize first
        removedPrize = player["prize"]
        availablePrizes.add_item(removedPrize)
        removedPrize.heldBy = None

    # Draw prize and give player
    availablePrizes.remove_item(drawnPrize)
    drawnPrize.heldBy = adminUsername
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

# TODO: This is too long
def peekPrizesCmd(update, context):
    username = update.message.chat.username
    chat_id = update.message.chat.id
    if username not in admins:
        bot.send_message(chat_id=chat_id,
            text="Only admins can use this command!\n\n" + dontWasteMyTimeText)
        return
    if username not in playerTracker:
        bot.send_message(chat_id=chat_id,
            text="Player hasn't registered yet :(\n\nPress /start")
        return
    printAvailablePrizes(chat_id=chat_id)
    printTakenPrizes(chat_id=chat_id)
    print(playerTracker)

# ===================Main Method============================

def main():

    # Load Game State
    loadGameState()

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

    # Save json file every 30s
    timeout = 30
    l = task.LoopingCall(saveGameState)
    l.start(timeout)
    reactor.run()


if __name__ == '__main__':
    main()
