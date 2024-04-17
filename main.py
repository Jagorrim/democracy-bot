import nextcord
import asyncio
import addition
import config
import pprint


class Democracy(nextcord.Client):
    def __init__(self):
        bot_intents = nextcord.Intents().all()

        nextcord.Client.__init__(self, intents=bot_intents, allowed_mentions=nextcord.AllowedMentions(everyone=True))
        self.create_poll = self.slash_command('create_poll', 'creating poll')(self.create_poll)
        self.requests_threads = {
            # thread_id: {
            #             'count': 0, (кол-во заявок, надо чтобы потом отсматривать из этого кол-ва сообщений заявки)
            #             'users': set(id юзеров, которые отправляли заявки)
            #             }
        }
        self.polls = {
            # thread_id: {
            #             message.id: {
            #                          'request': nextcord.Message (отправленная заявка со всеми данными),
            #                          'votes': 0
            #                          }
            #             }
        }

    async def create_poll(self,
                          interaction: nextcord.Interaction,
                          role_id: str,
                          time_to_request: int,
                          max_requests: int,
                          time_to_elect: int,
                          max_elected: int
                          ) -> None:
        if not (role_id.isdigit() and interaction.guild.get_role(int(role_id)) is not None):
            await interaction.send('Некорректное ID')
            return

        role_id = int(role_id)
        title = f'Приём заявок на голосование на роль {interaction.guild.get_role(role_id).mention}: '
        await interaction.send(title)

        original_message = await interaction.original_message()
        thread = await original_message.create_thread(name=title)

        self.requests_threads[thread.id] = {'count': 0,
                                            'users': set()}

        # Запускаем отдельный обработчик, который будет ждать время, отведённое на сбор заявок, а потом посчитает их
        await self.loop.create_task(self.proccess_requests(
            role_id, thread.id, time_to_request, max_requests, time_to_elect, max_elected
        ))

    async def vote(self, interaction: nextcord.Interaction) -> None:
        # Тут должен быть вызов метода, отправляющего вызвавшему команду юзеру голосование
        pass

    async def on_message(self, message: nextcord.Message) -> None:
        # Если в канале не проходит приём заявок
        if message.channel.id not in self.requests_threads:
            return

        # Если человек уже отправлял заявку
        if message.author.id in self.requests_threads[message.channel.id]['users']:
            await message.delete()
            return

        # Заносим заявку в "базу"
        self.requests_threads[message.channel.id]['users'].add(message.author.id)
        self.requests_threads[message.channel.id]['count'] += 1

        await message.add_reaction(config.approval_emoji)

    async def proccess_requests(self,
                                role_id: int,
                                thread_id: int,
                                time_to_request: int,
                                max_requests: int,
                                time_to_elect: int,
                                max_elected: int) -> None:
        await asyncio.sleep(time_to_request)

        channel = self.get_channel(thread_id)
        messages = await channel.history(
            limit=self.requests_threads[thread_id]['count']
        ).flatten()

        del self.requests_threads[thread_id]

        # Получаем те заявки, на которых стоит наибольшее количество "✅"
        messages = sorted(
            [(addition.approves_count(msg), msg) for msg in messages],
            key=lambda data: data[0], reverse=True
        )[:max_requests]

        # Заносим в "базу" данные о текущем голосовании
        self.polls[thread_id] = {}
        for supporters_count, message in messages:
            self.polls[thread_id][message.id] = {
                'request': message,
                'votes': 0,
                'supporters_count': supporters_count
            }
        pprint.pprint(self.polls)


if __name__ == '__main__':
    bot = Democracy()
    bot.run(config.token)
