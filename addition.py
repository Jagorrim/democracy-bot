import nextcord
import config


# Функция, получающая количество реакций "✅" на переданном сообщении
def approves_count(message: nextcord.Message) -> int:
    for reaction in message.reactions:
        if reaction.emoji == config.approval_emoji:
            return reaction.count - 1  # одну реакцию ставит бот, так что её надо вычесть

    return 0
