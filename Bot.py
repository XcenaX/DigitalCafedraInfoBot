# -*- coding: utf-8 -*-
import datetime
import telebot
from telebot import TeleBot, types

from threading import Thread
import csv
import pandas as pd
import os
from datetime import datetime

question_text = ''
QUESTIONS_PER_PAGE = 8
page = 1
exclude_logs = ["XcenaX", "the_northlord"]

class Bot():
    owners_file = "bot_data/owners.txt"
    users_file = "bot_data/users.txt"
    questions_file = "bot_data/questions.csv"
    main_questions_file = "bot_data/main_questions.csv"
    log_file = "bot_data/logs.txt"
    bot = None
    
    def __init__(self, settings):
        self.bot = telebot.TeleBot(settings["bot_token"])        
        self.owners_file =  os.path.join(settings["BASE_DIR"],self.owners_file)
        self.users_file = os.path.join(settings["BASE_DIR"],self.users_file)
        self.questions_file = os.path.join(settings["BASE_DIR"],self.questions_file)
        self.main_questions_file = os.path.join(settings["BASE_DIR"],self.main_questions_file)
        self.log_file = os.path.join(settings["BASE_DIR"],self.log_file)

        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.add_user(message.from_user.id)
            self.show_main_menu(message)                        


        @self.bot.message_handler(content_types=['text'])
        def main(message):                              
            if "Спросить вопрос" in message.text:                
                send = self.bot.send_message(message.chat.id, "Выберите вопрос: ", reply_markup=self.get_questions_keyboard())
                self.bot.register_next_step_handler(send, self.main_question)
            elif "Другой вопрос" == message.text:
                send = self.bot.send_message(message.chat.id, "Напишите вопрос: ", reply_markup=self.get_cancel_keyboard())
                self.bot.register_next_step_handler(send, self.another_question)                
            elif "Добавить вопрос" in message.text:
                if self.check_owner(message.from_user.id):        
                    send = self.bot.send_message(message.chat.id, "Напишите текст вопроса: ", reply_markup=self.get_cancel_keyboard())
                    self.bot.register_next_step_handler(send, self.create_question)                
            elif "Удалить вопрос" in message.text:
                if self.check_owner(message.from_user.id):        
                    send = self.bot.send_message(message.chat.id, "Выбрите вопрос: ", reply_markup=self.get_delete_question_keyboard())
                    self.bot.register_next_step_handler(send, self.search_question)                
            elif "Отмена" == message.text:
                self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
                self.show_main_menu(message)               
            else:
                self.bot.send_message(message.chat.id, "Я тебя не понимаю")
                self.show_main_menu(message)               
            # try:
            #     self.bot.delete_message(message.chat.id, message.id)
            # except:
            #     pass
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_question(call):                        
            if "Отмена" == call.data:
                self.bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
                self.show_main_menu(call.message)                

    def another_question(self, message):
        if message.text == "Отмена":
            self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
            self.show_main_menu(message)
        else:
            questions = self.get_questions(questions_type="all")
            answer = "Извини, на этот вопрос я не знаю ответа. Попробуй задать другой вопрос"    
            for question in questions:
                if str(question["question"]).lower() == str(message.text).lower():
                    answer = question["answer"]
                    break
            send = self.bot.send_message(message.chat.id, answer, reply_markup=self.get_cancel_keyboard())
            self.bot.register_next_step_handler(send, self.another_question)     

    def main_question(self, message):
        if message.text == "Отмена":
            self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
            self.show_main_menu(message)
        elif message.text == "Другой вопрос":
            send = self.bot.send_message(message.chat.id, "Напишите свой вопрос", reply_markup=self.get_cancel_keyboard())
            self.bot.register_next_step_handler(send, self.another_question)
        else:
            questions = self.get_questions(questions_type="main")
            answer = ""    
            for question in questions:
                if question["question"] == message.text:
                    answer = question["answer"]
                    break
            send = self.bot.send_message(message.chat.id, answer, reply_markup=self.get_questions_keyboard())
            self.bot.register_next_step_handler(send, self.main_question)    

    def create_question(self, message):
        global question_text 
        if message.text == "Отмена":
            self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
            self.show_main_menu(message)
        else:
            question_text = message.text
            send = self.bot.send_message(message.chat.id, "Введите ответ на этот вопрос", reply_markup=self.get_cancel_keyboard())
            self.bot.register_next_step_handler(send, self.create_question2)   
    
    def create_question2(self, message):
        global question_text
        if message.text != "Отмена":
            question_answer = message.text
            self.add_question(question_text,  question_answer)
            if message.from_user.username not in exclude_logs:
                now = datetime.now()
                dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
                log = dt_string + " | " + message.from_user.username + " создал вопрос: (" + question_text + ") с ответом (" + question_answer + ")"
                self.add_log(log)
        self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
        self.show_main_menu(message)    

    def search_question(self, message):
        global page
        count_questions = len(self.get_questions(questions_type='all'))
        if message.text == "Отмена":
            self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
            self.show_main_menu(message)  
            return 
        elif message.text == "Дальше":
            if page * QUESTIONS_PER_PAGE < count_questions:
                page += 1
        elif message.text == "Назад":
            if page > 1:
                page -= 1
        else:
            question = self.get_question(str(message.text), 'all')
            if question:
                text = question["question"]
                answer = question["answer"]
                self.remove_question(question["question"])
                self.bot.send_message(message.chat.id, "Вопрос успешно удалён!")      
                if message.from_user.username not in exclude_logs:
                    now = datetime.now()
                    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
                    log = dt_string + " | " + message.from_user.username + " удалил вопрос: (" + text + ") с ответом (" + answer + ")"
                    self.add_log(log)
            else:
                self.bot.send_message(message.chat.id, "Что-то пошло не так! Вопрос не удалён!")                
            self.bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
            self.show_main_menu(message)
            return

        send = self.bot.send_message(message.chat.id, "Выберите вопрос", reply_markup=self.get_delete_question_keyboard(page=page))
        self.bot.register_next_step_handler(send, self.search_question)   

    def show_main_menu(self, message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        ask_question = types.KeyboardButton("Спросить вопрос 📝")
        add_question = types.KeyboardButton("Добавить вопрос ➕")
        remove_question = types.KeyboardButton("Удалить вопрос ➖")
        
        markup.add(ask_question)
            
        if self.check_owner(message.from_user.id):
            markup.add(add_question)
            markup.add(remove_question)

        self.bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)

    def get_owners(self):
        with open(self.owners_file) as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        return content

    def get_users(self):
        with open(self.users_file) as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        return content
    
    def add_log(self, text):
        with open(self.log_file, "a", encoding='utf-8') as f:
            f.write("\n"+text)

    def get_questions(self, questions_type):
        file = self.questions_file if questions_type == "all" else self.main_questions_file
        questions = []
        with open(file, encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:                
                if line_count > 0:                    
                    data = {"question": row[0], "answer": row[1]}                    
                    questions.append(data)    
                line_count+=1
        return questions
    
    def get_question(self, question_text, question_type='main'):
        questions = self.get_questions(question_type)
        for question in questions:
            if question["question"] == question_text:
                return question
        return None

    def add_question(self, question, answer):
        with open(self.questions_file, mode='a', encoding="utf-8", newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=',')
            writer.writerow([question, answer])        
    
    def remove_question(self, text):
        df = pd.read_csv(self.questions_file, delimiter=',')
        df = df.loc[df["question"] != text]       
        print(df)
        df.to_csv(self.questions_file, index=False)       

    def add_user(self, id):
        id = str(id)
        users = self.get_users()
        if id not in users:
            with open(self.users_file, "a") as f:
                f.write("\n"+id)

    def check_owner(self, name):
        name = str(name)
        owners = self.get_owners()
        if name in owners:
            return True
        return False

    def check_date_format(self, date):
        try:
            datetime.datetime.strptime(date, "%Y.%m.%d %H:%M")
        except:
            return False
        return True


    def get_main_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
        ask_question = types.InlineKeyboardButton(text="Спросить вопрос", callback_data="ask_question")
        add_question = types.InlineKeyboardButton(text="Добавить вопрос", callback_data="add_question")
        keyboard.add(ask_question)
        keyboard.add(add_question)
        return keyboard
    
    def get_delete_question_keyboard(self, page=1):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
        questions = self.get_questions("all")
        length = len(questions)
        end = QUESTIONS_PER_PAGE*page
        start = end - QUESTIONS_PER_PAGE
        data = questions[start : end]
        for question in data:
            current_question = types.KeyboardButton(question["question"])          
            keyboard.add(current_question)
        cancel = types.KeyboardButton("Отмена")          
        _next = types.KeyboardButton("Дальше")          
        prev = types.KeyboardButton("Назад")          
        keyboard.add(cancel)
        if length - end > 0:
            keyboard.add(_next)
        if start >= 1:
            keyboard.add(prev)
        return keyboard

    def get_user_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
        ask_question = types.InlineKeyboardButton(text="Спросить вопрос", callback_data="ask_question")
        keyboard.add(ask_question)
        return keyboard

    def get_cancel_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
        cancel = types.InlineKeyboardButton(text="Отмена", callback_data="cancel")
        keyboard.add(cancel)
        return keyboard

    def get_questions_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
        questions = self.get_questions("main")
        for question in questions:
            current_question = types.InlineKeyboardButton(text=question["question"])
            keyboard.add(current_question)
        another_question = types.KeyboardButton("Другой вопрос")            
        cancel = types.InlineKeyboardButton(text="Отмена", callback_data="cancel")        
        keyboard.add(another_question)
        keyboard.add(cancel)        
        return keyboard

    def start_bot(self):
        self.bot.polling(none_stop=True, interval=0)

