import json
import time

import undetected_chromedriver as uc

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from telethon import TelegramClient


class FootballTicketsBuyer():
    def __init__(self, telegram_client: TelegramClient):
        self.headless = False
        self.driver: WebDriver
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        self.telegram_client = telegram_client
        self.telegram_user = ""

        self.minimum_seats_in_row = 10
        self.max_tickets_to_buy = 50
        
        # self.accounts = open("/Users/alialjazaeri/Downloads/football_tickets_buyer/accounts.txt", encoding="utf8").read().replace("\r", "").split("\n")
        # self.login_details = open("/Users/alialjazaeri/Downloads/football_tickets_buyer/credentials.txt", encoding="utf8").read().replace("\r", "").split("\n")[0].split(" ")
        self.accounts = open("accounts.txt", encoding="utf8").read().replace("\r", "").split("\n")
        self.login_details = open("credentials.txt", encoding="utf8").read().replace("\r", "").split("\n")[0].split(" ")
        self.already_logedin = False

        self.website_url = "https://book.nufc.co.uk/"
        self.login_page = "https://login.nufc.co.uk/auth/login?mandatory=true"
        self.tickets_page = "https://book.nufc.co.uk/en-GB/categories/Home%20Tickets"
        self.cart_url = "https://book.nufc.co.uk/Order.aspx"

        self.team_to_look_for = "newcastle united"

        self.selectors = {
            "email": "EmailAddress",
            "password": "password",
            "button": ".button.pull-right.g-recaptcha",
            "matches_list": ".itemsList .dataItem",
            "match_name": ".name",
            "match_id": ".venueAreas.venueAreasControl",
            "add_to_basket_btn": "//*[contains(@class, 'addToBasket') and not(contains(@class, 'disabled'))]",
            "price_type": ".priceType",
            "price_types": ".tickets .row",
            "ticket_incrementer": ".ops a.ui-spinner-up",
            "order_btn": "#btnProceed",
            "owners": ".basketTickets .basketItem .owner",
            "find_btn": "#qtip-0 .button-find",
            "supporter_id": "input[name='crmId']",
            "postcode": "input[name='zipCode']",
            "lookup_btn": "#lookupCustomer .find",
        }
        
    def load_config(self):
        # /Users/alialjazaeri/Downloads/football_tickets_buyer/config.txt
        with open("config.txt", encoding="utf8") as f:
            config = f.read().replace("\r", "").split("\n")
            
            for item in config:
                if len(item.strip()) == 0:
                    continue
                
                item = item.strip().split(" ")
                
                if item[0] == "max_tickets_to_buy":
                    self.max_tickets_to_buy = int(item[1])
                    
                elif item[0] == "minimum_seats_in_row":
                    self.minimum_seats_in_row = int(item[1])
                
                elif item[0] == "telegram_user":
                    self.telegram_user = str(item[1])

    def init_webdriver(self):
        options = uc.ChromeOptions()

        options.add_argument("--log-level=4")
        options.add_argument(f'--profile-directory=defualt')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument("--use-fake-device-for-media-stream")
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-notifications")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-zygote')
        options.add_argument(f"user-agent={self.user_agent}")

        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_setting_values.notifications": 1,
            "excludeSwitches": ["enable-automation", "disable-popup-blocking"],
            'useAutomationExtension': False,
        })

        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {"performance": "ALL"}

        self.driver = uc.Chrome(
            options=options, desired_capabilities=capabilities, headless=self.headless)

        self.driver.maximize_window()
        self.driver.set_page_load_timeout(5*60)  # 5 minutes
        
        try:
            # /Users/alialjazaeri/Downloads/football_tickets_buyer/
            cookies = json.loads(open("cookies.txt", encoding="utf8").read())
            
            for cookie in cookies:
                self.driver.add_cookie(cookie)
        except:
            ...

    def login(self) -> bool:
        print("Trying to login into the website...")
        try:
            self.driver.get(self.login_page)
            
            if self.driver.current_url.find(".queue-it.net/") != -1:
                self.wait_in_the_queue()

            self.driver.find_element(By.ID, self.selectors["email"]).send_keys(self.login_details[0])
            self.driver.find_element(By.ID, self.selectors["password"]).send_keys(self.login_details[1])

            self.driver.find_element(By.CSS_SELECTOR, self.selectors["button"]).click()

            self.sleep_for_x_mins(10/60)

            return True
        except:
            return False

    def extract_seats_list(self) -> 'list[dict]':
        src = self.driver.page_source

        seats_list_1 = src.find('require(["js/eventPage"], function(module){')

        if seats_list_1 == -1:
            return []

        seats_list_2 = src.find('[{', seats_list_1)
        seats_list_3 = src.find('}]', seats_list_2)

        seats_list = src[seats_list_2:seats_list_3] + "}]"

        try:
            seats_list = json.loads(seats_list)
            return seats_list
        except:
            return []

    def page_has_loaded(self) -> bool:
        page_state = self.driver.execute_script('return document.readyState;')
        return page_state == 'complete'
    
    def save_queueit_cookies(self):
        cookies = self.driver.get_cookies()
        
        required_cookies = []
        
        for cookie in cookies:
            cookie: 'dict[str,str]' = cookie
            if (cookie["name"].lower().startswith("queue-it")):
                required_cookies.append(cookie)
        
        open("cookies.txt", "w+", encoding="utf8").write(json.dumps(required_cookies))
    
    def wait_in_the_queue(self):
        print("Waiting in the queue-it room...")
        self.save_queueit_cookies()
        
        while True:
            if self.driver.current_url.find(".queue-it.net/") == -1:
                break
            
            self.save_queueit_cookies()
        
        while True:
            if self.page_has_loaded():
                break
        
        print("Wait is over! Starting the process...")
    
    def assign_to_accounts(self) ->'tuple[bool, int, str]':
        warning = False
        
        print("Assigning tickets to accounts...")
        
        self.driver.get(self.cart_url)
        owners = self.driver.find_elements(By.CSS_SELECTOR, self.selectors["owners"])
        
        if len(owners) > len(self.accounts):
            owners = owners[:len(self.accounts)]
            warning = True
            
        for i in range(len(owners)):
            try:
                owner = owners[i]
                account = self.accounts[i].split(" ")
                    
                owner.click()
                    
                self.driver.find_element(By.CSS_SELECTOR, self.selectors["find_btn"]).click()
                self.sleep_for_x_mins(1.2/60)
                    
                self.driver.find_element(By.CSS_SELECTOR, self.selectors["supporter_id"]).send_keys(account[0])
                self.driver.find_element(By.CSS_SELECTOR, self.selectors["postcode"]).send_keys(account[1])
                    
                self.driver.find_element(By.CSS_SELECTOR, self.selectors["lookup_btn"])
                self.sleep_for_x_mins(1.5/60)
            except:
                ...
        
        if warning:
            return True, len(owners), "Warning: There are more tickets than accounts. Please either remove the tickets from basket or assign to new accounts manually."
        
        return True, len(owners), ""
        
    def goto_web(self) -> bool:
        if not self.already_logedin:
            success = self.login()
            
            if success:
                self.already_logedin = True
                print("Login Successful!")
                
                while True:
                    if self.page_has_loaded():
                        self.driver.get(self.tickets_page)
                        break
                    
                return True

            return False
        
        try:
            self.driver.get(self.tickets_page)
            return True        
        except:
            return False

    def is_sale_open(self) -> 'tuple[bool, list[str]]':
        valid_matches = []

        print("Checking if any match in open...")
        
        if self.driver.current_url.find(".queue-it.net/") != -1:
            self.wait_in_the_queue()
        
        try:
            matches = self.driver.find_elements(By.CSS_SELECTOR, self.selectors["matches_list"])

            for match in matches:
                try:
                    match_name = match.find_element(By.CSS_SELECTOR, self.selectors["match_name"]).text.strip().lower()

                    if match_name.startswith(self.team_to_look_for):
                        is_open = match.find_element(By.XPATH, self.selectors["add_to_basket_btn"])

                        if is_open:
                            url = is_open.find_element(By.TAG_NAME, "a").get_attribute("data-clickevent")
                            valid_matches.append(url)
                except:
                    ...

            if len(valid_matches) > 0:
                return True, list(set(valid_matches))

            return False, valid_matches
        except:
            return False, valid_matches

    def is_required_num_of_tickets_available(self, matches: 'list[str]') -> 'tuple[bool, list[list[dict]]]':
        valid_matches = []

        while True:
            print("\033c")
            print(f"Checking if required number of tickets (minimum: {self.minimum_seats_in_row}) are available in opened match(es)")
            
            for match in matches:
                try:
                    self.driver.get(f"{self.website_url}{match}")
                    
                    seats = self.extract_seats_list()
                    
                    match_id = self.driver.find_element(By.CSS_SELECTOR, self.selectors["match_id"]).get_attribute("data-productid")

                    if len(seats) == 0:
                        continue
                    
                    valid_matches.append([])
                    
                    for seat in seats:
                        if seat["type"] == "SelectedSeat" and seat["free"] > self.minimum_seats_in_row and not seat["soldOut"] and not seat["isBlocked"]:
                            valid_matches[len(valid_matches) - 1].append({
                                "match": f"{self.website_url}{match}".replace("hallmap", ""),
                                "match_id": match_id,
                                "seat_id": seat["name"],
                                "area_id": seat["guid"],
                                "seats_free": seat["free"],
                            })
                    
                    self.sleep_for_x_mins(1/60)
                except:
                    ...

            if len(valid_matches) > 0:
                if len(valid_matches[0]) > 0:
                    return True, valid_matches
            else:
                print("No tickets available!")
            
            time.sleep(2)

    def is_all_seats_in_row(self, matches: 'list[list[dict]]') -> bool:
        success = 0
        
        print("Checking if seats are in a row and adding them to basket...")
        
        for match in matches:
            for area in match:
                tickets_added = 0
                
                if tickets_added >= self.max_tickets_to_buy:
                    break
                
                url = f'{area["match"]}area={area["area_id"]}&ype=ba&sb2m=1&noredir&selMode=ba'
                self.driver.get(url)
                
                try:
                    available_price_types = self.driver.find_elements(By.CSS_SELECTOR, self.selectors["price_types"])
                    for price_type in available_price_types:
                        txt = price_type.find_element(By.CSS_SELECTOR, self.selectors["price_type"]).text
                        
                        if txt.strip().lower() == "adult":
                            for _ in range(self.minimum_seats_in_row):
                                price_type.find_element(By.CSS_SELECTOR, self.selectors["ticket_incrementer"]).click()
                            
                            self.driver.find_element(By.CSS_SELECTOR, self.selectors["order_btn"]).click()
                            self.sleep_for_x_mins(1.2/60)
                            
                            if self.driver.current_url == url:
                                break
                            
                            success += 1
                            tickets_added += self.minimum_seats_in_row
                        
                        break
                except:
                    ...
        
        if success > 0:
            return True
        
        return False

    def notify_user(self, msg: str) -> bool:
        try:
            self.telegram_client.loop.run_until_complete(self.telegram_client.send_message(self.telegram_user, message=msg))
            return True
        except:
            return False

    def sleep_for_x_mins(self, mins: int) -> bool:
        time.sleep(mins*60)

    def buy(self):
        
        print("Loading config and chrome...")
        self.load_config()
        self.init_webdriver()
        
        try:
            print("Starting the bot processes...")
            while True:
                success = self.goto_web()
                
                if success:
                    print("\033c")
                    print(f"Website loaded: {self.tickets_page}")
                    success, _matches = self.is_sale_open()
                    
                    if success:
                        print(f"These matches are open (count: {len(_matches)}): {_matches}")
                        success, matches = self.is_required_num_of_tickets_available(matches=_matches)
                        
                        if success:
                            print("Tickets available!")
                            success = self.is_all_seats_in_row(matches=matches)
                            
                            if success:
                                print("Required number of tickets are added to basket!")
                                success, tickets_added, warning = self.assign_to_accounts()
                                
                                if success:
                                    print("Tickets Assigned!")
                                    msg = f"The bot has added {tickets_added} tickets of {len(_matches)} match(es), and also assigned them to accounts. Please buy them ASAP!"
                                    
                                    if len(warning) > 0:
                                        msg += "\n" + warning
                                    
                                    print("Sending success message to user in telegram")
                                    
                                    success = self.notify_user(msg=msg)

                                    if success:
                                        print("Everything worked perfectly! Bot will look for open matches again after 30 seconds!")
                                    else:
                                        print(f"Error while sending msg to user in whatsapp! Here's the message: {msg}")
                                else:
                                    print("Error while assinging tickets to accounts! Will try again after 30 seconds...")
                            else:
                                print("Tickets available but not in row!")
                        else:
                            print("No tickets available!")
                    else:
                        print("Sale is not open yet!")
                else:
                    print("Error while login! Will try again after 5 seconds...")
                    
                self.sleep_for_x_mins(5/60)

        except Exception as e:
            print(f"An error occured: {e}")
            self.driver.quit()
            
        self.driver.quit()


if __name__ == "__main__":
    telegram_client = TelegramClient(session='anon', api_id=21534417, api_hash='a40defa79825f22181cf58b358be51e6')
    telegram_client.start(bot_token="6232640512:AAHadbkt0oX44seMflJhVoWEf8Tp-8SAPTM")
    
    tickets_buyer = FootballTicketsBuyer(telegram_client=telegram_client)
    tickets_buyer.buy()
    

# Queue-it-a50ec075-5aad-4dc4-9b38-b27359a5ac56 -> uifh=1oXK7Bk5BqTq2sP3BOn9yKLUyY_AIiFlawVTLnDJtylQgOjpRjzjojmA2g6z0dkC0&WasRedirected=false&i=638163714117458068
# Queue-it-nufc________________nufc6april202310am -> Qid=a50ec075-5aad-4dc4-9b38-b27359a5ac56&Cid=en-GB&f=0
# Queue-it -> u=92b0d8a5-faa6-4046-95cf-9dcede568c85
