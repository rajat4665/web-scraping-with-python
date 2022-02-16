#!/usr/bin/env python
# coding: utf-8

#Requirements
#pip3 install requests
#pip3 install bs4

#run in the browser also what are you doing with the help of chrome driver

# ## Basic fundamentals of web scraping

# import these two modules bs4 for selecting HTML tags easily
from bs4 import BeautifulSoup
# requests module is easy to operate some people use urllib but I prefer this one because it is easy to use.
import requests
from selenium import webdriver

# I put here my own blog url ,you can change it.
url="https://getpython.wordpress.com/"
BASE_URL = "https://getpython.wordpress.com/"
#Requests module use to data from given url
source=requests.get(url)


def get_chrome_web_driver(options):
    return webdriver.Chrome("./chromedriver", chrome_options=options)


def get_web_driver_options():
    return webdriver.ChromeOptions()


def set_ignore_certificate_error(options):
    options.add_argument('--ignore-certificate-errors')


def set_browser_as_incognito(options):
    options.add_argument('--incognito')

# BeautifulSoup is used for getting HTML structure from requests response.(craete your soup)
soup=BeautifulSoup(source.text,'html')

# Find function is used to find a single element if there are more than once it always returns the first element.
title=soup.find('title') # place your html tagg in parentheses that you want to find from html.
print("this is with html tags :",title)

qwery=soup.find('h1') # here i find first h1 tagg in my website using find operation.

#use .text for extract only text without any html tags
print("this is without html tags:",qwery.text) 


links=soup.find('a') #i extarcted link using "a" tag
print(links)


# ## extarct data from innerhtml 

# here i extarcted href data from anchor tag.
print(links['href']) 

##  or another way
##extracting href(links) attribute and anchor(<a>) tag from page 
for a in soup.find_all('a', href=True):
    print ( a['href'])

for i in links:
    print(i.text)

# similarly i got class details from a anchor tag
print(links['class'])


# ## findall operation in Bs4

# findall function is used to fetch all tags at a single time.
many_link=soup.find_all('a') # here i extracted all the anchor tags of my website
total_links=len(many_link) # len function is use to calculate length of your array
print("total links in my website :",total_links)
print()
for i in many_link[:6]: # here i use slicing to fetch only first 6 links from rest of them.
    print(i)

second_link=many_link[1] #here i fetch second link which place on 1 index number in many_links.
print(second_link)
print()
print("href is :",second_link['href']) #only href link is extracted from ancor tag


# select div tag from second link
nested_div=second_link.find('div')
# As you can see div element extarcted , it also have inner elements
print(nested_div)
print()
#here i extracted class element from div but it give us in the form of list
z=(nested_div['class'])
print(z)
print(type(z))
print()
#  " " .join () method use to convert list type  into string type
print("class name of div is :"," ".join(nested_div['class'])) 


# ## scrap data from wikipedia

wiki=requests.get("https://en.wikipedia.org/wiki/World_War_II")
soup=BeautifulSoup(wiki.text,'html')
print(soup.find('title'))


# ### find html tags with classes

ww2_contents=soup.find_all("div",class_='toc')
for i in ww2_contents:
    print(i.text)


overview=soup.find_all('table',class_='infobox vevent')
for z in overview:
    print(z.text)
  
images=soup.find_all('img')

images
##or
print(images)

