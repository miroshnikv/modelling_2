import simpy
import random
import math
from enum import Enum


# перечисление, задающее тип клиента
class CustomerType(Enum):
    HOT = 1,
    COLD = 2,
    DRINK = 3

SIM_TIME = 90 * 60      # время симуляции

CASH_DESK_NUMBER = 2    # число касс
HOT_MEAL_WORKERS = 1    # число сотрудников на выдаче горячих блюд
COLD_MEAL_WORKERS = 1   # число сотрудников на выдаче холодных закусок

HOT_MEAL_MIN = 50       # минимальное время обслуживания на выдаче горячих блюд
HOT_MEAL_MAX = 120      # максимальное время обслуживания на выдаче горячих блюд
COLD_MEAL_MIN = 60      # минимальное время обслуживания на выдаче холодных закусок
COLD_MEAL_MAX = 180     # максимальное время обслуживания на выдаче холодных закусок

hot_wait = []           # время в очереди на выдаче горячих блюд
cold_wait = []          # время в очереди на выдаче холодных закусок
cdesk_wait = []         # время в очереди на кассе

hot_now = 0             # количество человек в очереди на выдаче горячих блюд
cold_now = 0            # количество человек в очереди на выдаче холодных закусок
cdesk_now = 0           # количество человек в очереди на кассе
max_hot = 0             # максимальное количество человек в очереди на выдаче горячих блюд
max_cold = 0            # максимальное количество человек в очереди на выдаче холодных закусок
max_cdesk = 0           # максимальное количество человек в очереди на кассе
hot_av = []             # время ожидания на выдаче горячих блюд
cold_av = []            # время ожидания на выдаче холодных закусок
cdesk_av = []           # время ожидания на кассе

hot_client = []         # время в системе клиентов первого типа
cold_client = []        # время в системе клиентов второго типа
drink_client = []       # время в системе клиентов третьего типа

customers_max = 0       # максимальное количество клиентов в системе
customers_now = 0       # количество клиентов в системе
customers_time = []     # время, проведенное клиентом в системе

env = simpy.Environment()                                 # инициализируем среду моделирования
hot = simpy.Resource(env, capacity=HOT_MEAL_WORKERS)      # ресурс обслуживания на выдаче горячих блюд
cold = simpy.Resource(env, capacity=COLD_MEAL_WORKERS)    # ресурс обслуживания на выдаче холодных закусок
cdesk = simpy.Resource(env, capacity=CASH_DESK_NUMBER)    # ресурс обслуживания на кассах


class Customer(object):
    def __init__(self, env, way):
        self.env = env
        self.way = way

    def run(self):
        # инициализируем вспомогательные счетчики
        cdesk_time = 0
        start_time = time = self.env.now
        wait = 0
        global hot_wait, cold_wait, cdesk_wait, customers, hot_av, cold_av, cdesk_av
        global hot_now, cold_now, cdesk_now, max_hot, max_cold, max_cdesk
        global hot_client, cold_client, drink_client
        global customers_max, customers_now, customers_time

        # клиент пришел в систему - увеличиваем счетчик
        customers_now += 1
        # если нужно, обновляем максимальное значение
        if customers_now > customers_max:
            customers_max = customers_now

        # для клиентов первого типа
        if self.way == CustomerType.HOT:
            hot_now += 1

            if hot_now > max_hot:
                max_hot = hot_now

            # запрашиваем ресурс
            with hot.request() as req:
                # клиент ждет в очереди
                yield req

                # сбор статистики
                queue_wait = self.env.now
                hot_wait.append(queue_wait - time)
                wait += queue_wait - time
                service_duration = random.randint(HOT_MEAL_MIN, HOT_MEAL_MAX)
                hot_av.append(queue_wait - time + service_duration)

                # накопляемое время оплаты
                cdesk_time += random.randint(20, 40)
                # клиент обслуживается
                yield self.env.timeout(service_duration)
                hot_now -= 1

        # для клиентов второго типа
        elif self.way == CustomerType.COLD:
            cold_now += 1

            if cold_now > max_cold:
                max_cold = cold_now

            # запрашиваем ресурс
            with cold.request() as req:
                # клиент ждет в очереди
                yield req

                # сбор статистики
                queue_wait = self.env.now
                cold_wait.append(queue_wait - time)
                wait += queue_wait - time
                service_duration = random.randint(COLD_MEAL_MIN, COLD_MEAL_MAX)
                cold_av.append(queue_wait - time + service_duration)

                # накопляемое время оплаты
                cdesk_time += random.randint(5, 15)
                # клиент обслуживается
                yield self.env.timeout(service_duration)
                cold_now -= 1

        # все обслуживаются на выдаче напитков
        service_duration = random.randint(5, 20)

        # накопляемое время оплаты
        cdesk_time += random.randint(5, 15)
        yield self.env.timeout(service_duration)

        time = self.env.now
        cdesk_now += 1
        if cdesk_now > max_cdesk:
            max_cdesk = cdesk_now

        # запрашиваем ресурс кассы
        with cdesk.request() as req:
            # клиент ждет в очереди
            yield req

            # сбор статистики
            queue_wait = self.env.now
            cdesk_wait.append(queue_wait - time)
            wait += queue_wait - time
            cdesk_av.append(queue_wait - time + cdesk_time)

            # клиент обслуживается
            yield self.env.timeout(cdesk_time)
            cdesk_now -= 1

        if self.way == CustomerType.HOT:
            hot_client.append(wait)
        elif self.way == CustomerType.COLD:
            cold_client.append(wait)
        else:
            drink_client.append(wait)

        # клиент ушел из системы - уменьшаем счетчик
        customers_now -= 1
        customers_time.append(self.env.now - start_time)


# вычисление количества пришедших клиентов в соответствии с данными вероятностями
def customer_count():
    r = random.uniform(0, 1)
    if r <= 0.5:
        return 1
    if r <= 0.8:
        return 2
    if r <= 0.9:
        return 3
    return 4


# определение пути клиента по кафетерию в соответствии с данными вероятностями
def customer_way():
    r = random.uniform(0, 1)
    if r <= 0.8:
        return CustomerType.HOT
    if r <= 0.95:
        return CustomerType.COLD
    return CustomerType.DRINK


# определение промежутка времени между новыми посетителями
def customer_arrive(env):
    while env.now < (SIM_TIME - 30):
        yield env.timeout(math.floor(random.expovariate(1 / 30)))
        num = customer_count()
        for i in range(num):
            customer = Customer(env, customer_way())
            env.process(customer.run())

# запускаем процесс моделирования
env.process(customer_arrive(env))
env.run(until=SIM_TIME)

#печатаем статистическую информацию после моделирования
print("На выдаче горячих блюд:")
print("Максимальное время задержки {0} мин {1} сек, среднее время задержки {2} мин {3} сек".format(max(hot_wait) // 60,
      max(hot_wait) % 60, int(sum(hot_wait) / len(hot_wait)) // 60, int(sum(hot_wait) / len(hot_wait)) % 60))
print("Максимальное количество клиентов {0}, среднее время в очереди {1} мин {2} сек".format
      (max_hot, int(sum(hot_av) / len(hot_av)) // 60, int(sum(hot_av) / len(hot_av)) % 60))

print("На выдаче холодных блюд:")
print("Максимальное время задержки {0} мин {1} сек, среднее время задержки {2} мин {3} сек".format(max(cold_wait) // 60,
      max(cold_wait) % 60, int(sum(cold_wait) / len(cold_wait)) // 60, int(sum(cold_wait) / len(cold_wait)) % 60))
print("Максимальное количество клиентов {0}, среднее время в очереди {1} мин {2} сек".format
      (max_cold, int(sum(cold_av) / len(cold_av)) // 60, int(sum(cold_av) / len(cold_av)) % 60))

print("На кассах:")
print("Максимальное время задержки {0} мин {1} сек, среднее время задержки {2} мин {3} сек".format
      (max(cdesk_wait) // 60, max(cdesk_wait) % 60, int(sum(cdesk_wait) / len(cdesk_wait)) // 60,
       int(sum(cdesk_wait) / len(cdesk_wait)) % 60))
print("Максимальное количество клиентов {0}, среднее время в очереди {1} мин {2} сек\n".format
      (max_cdesk, int(sum(cdesk_av) / len(cdesk_av)) // 60, int(sum(cdesk_av) / len(cdesk_av)) % 60))

print("Для посетителей первого типа:")
print("Максимальное время задержки во всех очередях {0} мин {1} сек, среднее {2} мин {3} сек".format
      (max(hot_client) // 60, max(hot_client) % 60, int(sum(hot_client) / len(hot_client)) // 60,
       int(sum(hot_client) / len(hot_client)) % 60))
print("Для посетителей второго типа:")
print("Максимальное время задержки во всех очередях {0} мин {1} сек, среднее {2} мин {3} сек".format
      (max(cold_client) // 60, max(cold_client) % 60, int(sum(cold_client) / len(cold_client)) // 60,
       int(sum(cold_client) / len(cold_client)) % 60))
print("Для посетителей третьего типа:")
print("Максимальное время задержки во всех очередях {0} мин {1} сек, среднее {2} мин {3} сек".format
      (max(drink_client) // 60, max(drink_client) % 60, int(sum(drink_client) / len(drink_client)) // 60,
       int(sum(drink_client) / len(drink_client)) % 60))

av = sum(hot_client) / len(hot_client) * 0.8 + sum(cold_client) / len(cold_client) * 0.15 \
     + sum(drink_client) / len(drink_client) * 0.05
print("Суммарная средняя задержка {0} мин {1} сек\n".format
      (int(av) // 60, int(av) % 60))

print("Для всех посетителей:")
print("Максимальное число в системе {0}".format(customers_max))
print("Среднее по времени нахождение в системе {0} мин {1} сек".format
      (int(sum(customers_time) / len(customers_time)) // 60, int(sum(customers_time) / len(customers_time)) % 60))
