import nextcord
import config


# Функция, получающая количество реакций "✅" на переданном сообщении
def approves_count(message: nextcord.Message):
    for reaction in message.reactions:
        if reaction.emoji == config.approval_emoji:
            return reaction.count

    return 0
