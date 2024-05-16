import nextcord
import asyncio
import addition
import config
from pprint import pprint


class Democracy(nextcord.Client):
    def __init__(self):
        bot_intents = nextcord.Intents().all()

        nextcord.Client.__init__(self, intents=bot_intents, allowed_mentions=nextcord.AllowedMentions(everyone=True))
        self.create_poll = self.slash_command('create_poll', 'creating poll')(self.create_poll)
        self.vote = self.slash_command('vote', 'use it to vote')(self.vote)

        self.requests = {}
        self.polls = {}

    async def create_poll(self,
                          interaction: nextcord.Interaction,
                          role_id: str,
                          time_to_request: int,
                          max_requests: int,
                          time_to_elect: int,
                          max_elected: int
                          ) -> None:
        if not (role_id.isdigit() and interaction.guild.get_role(int(role_id)) is not None):
            await interaction.send('Некорректное ID роли')
            return

        if interaction.channel_id in self.requests:
            await interaction.send('Здесь уже проводится сбор заявок!')
            return

        if interaction.channel_id in self.polls:
            await interaction.send('Здесь уже проводится голование!')
            return

        role_id = int(role_id)
        title = f'Приём заявок на голосование на роль {interaction.guild.get_role(role_id).mention}: '
        await interaction.send(title)

        # Если канал уже является тредом, то нам не надо создавать его, просто в нём запускаем голосование
        if isinstance(interaction.channel, nextcord.Thread):
            thread_id = interaction.channel_id
        else:
            original_message = await interaction.original_message()
            thread_id = (await original_message.create_thread(name=title)).id

        self.requests[thread_id] = {'count': 0,
                                    'users': set()}

        # Запускаем отдельный обработчик, который будет ждать время, отведённое на сбор заявок,
        # а потом посчитает их и запустит само голосование
        await self.process_requests(
            role_id, thread_id, time_to_request, max_requests, time_to_elect, max_elected
        )

    async def process_requests(self,
                               role_id: int,
                               thread_id: int,
                               time_to_request: int,
                               max_requests: int,
                               time_to_elect: int,
                               max_elected: int) -> None:
        await asyncio.sleep(time_to_request)

        channel = self.get_channel(thread_id)
        messages = await channel.history(
            limit=self.requests[thread_id]['count']
        ).flatten()

        del self.requests[thread_id]  # Заявки закрыты.

        # Получаем те заявки, на которых стоит наибольшее количество (и определённое их количество) "✅"
        messages = sorted(
            [(addition.approves_count(msg), msg) for msg in messages],
            key=lambda data: data[0], reverse=True
        )[:max_requests]

        # Заносим в "базу" данные о текущем голосовании
        self.polls[thread_id] = {
            'requests': [],
            'voters': set()

        }
        for supporters_count, message in messages:
            # Составляем, согласно описанному в readme паттерну, структуру заявок

            self.polls[thread_id]['requests'].append({
                'request': message,
                'votes': 0,
                'supporters_count': supporters_count
            })
        await channel.send('Голосование начато! Вызовите команду /vote здесь, и мы отправим вам бланки!')
        await self.process_voting(role_id, thread_id, time_to_elect, max_elected)

    async def process_voting(self,
                             role_id: int,
                             thread_id: int,
                             time_to_elect: int,
                             max_elected: int
                             ):
        pass

    async def on_message(self, message: nextcord.Message) -> None:
        # Если в канале не проходит приём заявок
        if message.channel.id not in self.requests:
            return

        # Если человек уже отправлял заявку
        if message.author.id in self.requests[message.channel.id]['users']:
            await message.delete()
            return

        # Заносим заявку в "базу"
        self.requests[message.channel.id]['users'].add(message.author.id)
        self.requests[message.channel.id]['count'] += 1

        await message.add_reaction(config.approval_emoji)

    async def vote(self, interaction: nextcord.Interaction) -> None:
        if interaction.channel_id not in self.polls:
            await interaction.send('Здесь не проходит голосование!', ephemeral=True)
            return

        if interaction.user.id in self.polls[interaction.channel_id]['voters']:
            await interaction.send('Вы уже голосовали!', ephemeral=True)
            return

        cur_person = 0
        requests = self.polls[interaction.channel_id]['requests']

        async def click_vote(_interaction: nextcord.Interaction):
            nonlocal cur_person
            self.polls[interaction.channel_id]['voters'].add(_interaction.user.id)  # добавляем юзера в проголосовавших
            self.polls[interaction.channel_id]['requests'][cur_person]['votes'] += 1  # Добавляем голос к кандидату

            await _interaction.message.edit(embed=None, content='Вы проголосовали!', view=None)

        async def click_get_prev(_interaction: nextcord.Interaction):
            nonlocal cur_person
            cur_person -= 1
            if cur_person < 0:
                cur_person = len(requests) - 1  # Если индекс ушёл в минус, то сделать его максимально возможным
            await update_embed(_interaction)

        async def click_get_next(_interaction: nextcord.Interaction):
            nonlocal cur_person
            cur_person += 1
            if cur_person > len(requests) - 1:  # Если индекс превысил максимум, то обнулить
                cur_person = 0
            await update_embed(_interaction)

        async def update_embed(_interaction: nextcord.Interaction):
            nonlocal cur_person
            embed = nextcord.Embed(
                title=requests[cur_person]['request'].author.global_name,  # Сюда мы вставляем текст с заявки
                description=requests[cur_person]['request'].content  # Текст заявки
            )

            embed.set_thumbnail(url=requests[cur_person]['request'].author.avatar)
            embed.set_footer(text=requests[cur_person]['supporters_count'])  # Количество подписей за кандидата
            await _interaction.message.edit(embed=embed)

        # Кнопка левого кандидата (в смысле промотать в левую сторону)
        btn_get_prev = nextcord.ui.Button(
            style=nextcord.ButtonStyle.gray,
            label="<-",
            custom_id="get_prev",  # кастом айди для подальшего взаимодействия с сообщением через него
        )
        btn_get_prev.callback = click_get_prev
        # Кнопка голосования
        btn_vote = nextcord.ui.Button(
            style=nextcord.ButtonStyle.blurple,
            label="+",
            custom_id="vote"  # Сохраняем плюсом айди чтобы по два раза не голосовали
        )
        # Кнопка правого кандидата (да, тоже промотать)
        btn_vote.callback = click_vote
        btn_get_next = nextcord.ui.Button(
            style=nextcord.ButtonStyle.gray,
            label="->",
            custom_id="get_next",
        )
        btn_get_next.callback = click_get_next

        embed = nextcord.Embed(
            title=requests[cur_person]['request'].author.global_name,  # Имя
            # (я без понятия, почему имя на сервере называется global_name)
            description=requests[cur_person]['request'].content  # Текст заявки
        )
        embed.set_thumbnail(url=requests[cur_person]['request'].author.avatar)
        embed.set_footer(text=requests[cur_person]['supporters_count'])  # Количество подписей за кандидата

        view = nextcord.ui.View()
        view.add_item(btn_get_prev)
        view.add_item(btn_vote)
        view.add_item(btn_get_next)

        await interaction.user.send(embed=embed, view=view)
        await interaction.send('Отправили бланки!', ephemeral=True)


if __name__ == '__main__':
    bot = Democracy()
    bot.run(config.token)
