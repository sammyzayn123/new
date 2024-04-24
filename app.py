# Import necessary libraries
from bs4 import BeautifulSoup as soup
import requests
import pandas as pd
import time
import os
import ssl
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin

# Define global paths for Image and CSV folders
IMG_FOLDER = os.path.join('static', 'images')
CSV_FOLDER = os.path.join('static', 'CSVs')

# Initialize Flask app
app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure environment variables
app.config['IMG_FOLDER'] = IMG_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER

# SSL certificate verification 
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Define a class for data collection
class DataCollection:
    '''
    Class meant for collection and management of data
    '''
    def __init__(self):
        self.data = {"Product": [], 
                     "Name": [],
                     "Price (INR)": [], 
                     "Rating": [], 
                     "Comment Heading": [], 
                     "Comment": []}

    def get_final_data(self, commentbox, prodName, prod_price):
        '''
        Append data gathered from comment box into data dictionary
        '''
        self.data["Product"].append(prodName)
        self.data["Price (INR)"].append(prod_price)
        self.data["Name"].append(commentbox.div.div.find_all('p', {'class': '_2sc7ZR _2V5EHH'})[0].text if commentbox.div.div.find_all('p', {'class': '_2sc7ZR _2V5EHH'}) else 'No Name')
        self.data["Rating"].append(commentbox.div.div.div.div.text if commentbox.div.div.div.div else 'No Rating')
        self.data["Comment Heading"].append(commentbox.div.div.div.p.text if commentbox.div.div.div.p else 'No Comment Heading')
        self.data["Comment"].append(commentbox.div.div.find_all('div', {'class': ''})[0].div.text if commentbox.div.div.find_all('div', {'class': ''}) else '')

    def get_main_HTML(self, base_URL, search_string):
        '''
        Return main html page based on search string
        '''
        search_url = f"{base_URL}/search?q={search_string}"
        page = requests.get(search_url).text
        return soup(page, "html.parser")

    def get_product_name_links(self, flipkart_base, bigBoxes):
        '''
        Returns list of (product name, product link)
        '''
        temp = []
        for box in bigBoxes:
            try:
                temp.append((box.div.div.div.a.img['alt'],
                             flipkart_base + box.div.div.div.a["href"]))
            except:
                pass
        return temp

    def get_prod_HTML(self, productLink):
        '''
        Returns each product HTML page after parsing it with soup
        '''
        prod_page = requests.get(productLink).text
        return soup(prod_page, "html.parser")

    def get_data_dict(self):
        '''
        Returns collected data in dictionary
        '''
        return self.data

    def save_as_dataframe(self, dataframe, fileName):
        '''
        Saves the dictionary dataframe as csv by given filename inside the CSVs folder
        '''
        csv_path = os.path.join(app.config['CSV_FOLDER'], f"{fileName}.csv")
        dataframe.to_csv(csv_path, index=None)
        return csv_path

    def save_wordcloud_image(self, dataframe, img_filename):
        '''
        Generates and saves the wordcloud image into wc_folder
        '''
        txt = dataframe["Comment"].values
        wc = WordCloud(width=800, height=400, background_color='black', stopwords=STOPWORDS).generate(str(txt))
        plt.figure(figsize=(20,10), facecolor='k', edgecolor='k')
        plt.imshow(wc, interpolation='bicubic') 
        plt.axis('off')
        plt.tight_layout()
        image_path = os.path.join(app.config['IMG_FOLDER'], f"{img_filename}.png")
        plt.savefig(image_path)
        plt.close()
        return image_path

class CleanCache:
    '''
    This class is responsible to clear any residual csv and image files present due to the past searches made.
    '''
    def __init__(self, directory):
        self.clean_path = directory
        if os.listdir(self.clean_path):
            for fileName in os.listdir(self.clean_path):
                os.remove(os.path.join(self.clean_path, fileName))

# Route to display the home page
@app.route('/', methods=['GET'])
@cross_origin()
def homePage():
    return render_template("index.html")

# Route to display the review page
@app.route('/review', methods=("POST", "GET"))
@cross_origin()
def index():
    if request.method == 'POST':
        try:
            base_URL = 'https://www.flipkart.com'
            search_string = request.form['content'].replace(" ", "+")
            start = time.perf_counter()
            get_data = DataCollection()
            flipkart_HTML = get_data.get_main_HTML(base_URL, search_string)
            bigBoxes = flipkart_HTML.find_all("div", {"class":"_1AtVbE col-12-12"})
            product_name_Links = get_data.get_product_name_links(base_URL, bigBoxes)
            for prodName, productLink in product_name_Links[:4]:
                for prod_HTML in get_data.get_prod_HTML(productLink):
                    try:
                        comment_boxes = prod_HTML.find_all('div', {'class': '_16PBlm'})
                        prod_price = float((prod_HTML.find_all('div', {"class": "_30jeq3 _16Jk6d"})[0].text.replace("₹", "")).replace(",", ""))
                        for commentbox in comment_boxes:
                            get_data.get_final_data(commentbox, prodName, prod_price)
                    except:
                        pass
            df = pd.DataFrame(get_data.get_data_dict())
            download_path = get_data.save_as_dataframe(df, fileName=search_string.replace("+", "_"))
            get_data.save_wordcloud_image(df, img_filename=search_string.replace("+", "_"))
            finish = time.perf_counter()
            print(f"Program finished with and timelapsed: {finish - start} second(s)")
            return render_template('review.html', tables=[df.to_html(classes='data')],
                                   titles=df.columns.values,
                                   search_string=search_string,
                                   download_csv=download_path)
        except Exception as e:
            print(e)
            return render_template("404.html")
    else:
        return render_template("index.html")

# Route to display wordcloud
@app.route('/show')
@cross_origin()
def show_wordcloud():
    img_file = os.listdir(app.config['IMG_FOLDER'])[0]
    full_filename = os.path.join(app.config['IMG_FOLDER'], img_file)
    return render_template("show_wc.html", user_image=full_filename)

if __name__ == '__main__':
    app.run(debug=True)
