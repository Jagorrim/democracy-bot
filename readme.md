Структура хранения заявок и голосований:

        self.requests_threads = {
              thread_id: {  # id канала, в котором отправляют заявки
                          'count': 0, (кол-во заявок, надо чтобы потом отсматривать из этого кол-ва сообщений заявки)
                          'users': set(id юзеров, которые отправляли заявки)
                          }
        }
        self.polls = {
              thread_id:  # id канала, в котором голосуют
                        {
                         'requests':  # список словарей, которые описывают заявку
                              [
                                  {
                                    'request': nextcord.Message (отправленная заявка со всеми данными),
                                    'votes': 0,
                                    'supporters_count': 0,
                                   }
                               ],
                          'voters': set(id юзеров, которые голосовали)
                         }
        }

  