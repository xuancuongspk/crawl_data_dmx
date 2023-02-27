import os 
import scrapy 
from bs4 import BeautifulSoup 
from lxml import etree

class Product(scrapy.Spider):
    name = 'dienmayxanh'

    def start_requests(self):
        # Get category url
        url = 'https://www.dienmayxanh.com/danh-muc-nhom-hang'
        yield scrapy.Request(url=url, callback=self.parse)
    
    def parse(self, response):
        categories = response.xpath('//ul[contains(@class, "lst-subcate")]/li[contains(@class, "subcate")]')
        for category in categories:
            li_class = category.xpath('./@class').get()
            category_id = li_class.split('-')[-1]
            if not category_id.isdigit():
                continue
            url = category.xpath('./a/@href').get() if 'www.dienmayxanh.com' in category.xpath('./a/@href').get() else os.path.join('https://www.dienmayxanh.com/', category.xpath('./a/@href').get())
            url = f'{url}#c={category_id}&o=13&pi=100'
            yield scrapy.Request(url=url, 
                                 callback=self.parse_category, 
                                 meta={'category_id': category_id, 
                                       'page': 1})
    
    def parse_category(self, response):
        list_product = response.xpath('//ul[@class="listproduct"]/li')
        for product in list_product:
            item = {}
            name = product.xpath('./a/@data-name').get()
            if not name:
                continue
            item['category'] = product.xpath('./a/@data-cate').get()
            item['name'] = name
            item['url'] = 'https://www.dienmayxanh.com' + product.xpath('./a/@href').get() if product.xpath('./a/@href').get() else None 
            item['old_price'] = product.xpath('.//*[contains(@class, "price-old")]/text()').get()
            item['price'] = product.xpath('.//*[@class="price"]/text()').get()
            item['percent'] = product.xpath('.//*[@class="percent"]/text()').get()
            yield scrapy.Request(url = item['url'], 
                                 callback=self.parse_detail,
                                 meta={'item': item})
        meta = response.meta
        url = f'https://www.dienmayxanh.com/Category/FilterProductBox?c={meta["category_id"]}&o=13&pi={meta["page"]}'
        yield scrapy.Request(url=url,
                                method='POST',
                                body="IsParentCate=False&IsShowCompare=True&prevent=true",
                                headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                                callback=self.parse_product, 
                                meta={'category_id': meta['category_id'], 
                                      'page': meta['page'] + 1})
        
    def parse_product(self, response):
        results = response.json()
        listproducts = results['listproducts']
        meta = response.meta
        if listproducts:
            # Crawl item
            soup = BeautifulSoup(listproducts)
            list_product = etree.HTML(str(soup))
            for product in list_product.xpath('//li'):
                item = {}
                name = product.xpath('./a/@data-name')
                if not name:
                    continue
                item['category'] = product.xpath('./a/@data-cate')[0]
                item['name'] = name[0]
                item['url'] = 'https://www.dienmayxanh.com' + product.xpath('./a/@href')[0] if product.xpath('./a/@href') else None 
                item['old_price'] = product.xpath('.//*[contains(@class, "price-old")]/text()')[0] if product.xpath('.//*[contains(@class, "price-old")]/text()') else None 
                item['price'] = product.xpath('.//*[@class="price"]/text()')[0] if product.xpath('.//*[@class="price"]/text()') else None 
                item['percent'] = product.xpath('.//*[@class="percent"]/text()')[0] if product.xpath('.//*[@class="percent"]/text()') else None 
                yield scrapy.Request(url = item['url'], 
                                 callback=self.parse_detail,
                                 meta={'item': item})
            # Next page
            url = f'https://www.dienmayxanh.com/Category/FilterProductBox?c={meta["category_id"]}&o=13&pi={meta["page"]}'
            print(url)
            yield scrapy.Request(url=url,
                                method='POST',
                                body="IsParentCate=False&IsShowCompare=True&prevent=true",
                                headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                                callback=self.parse_product, 
                                meta={'category_id': meta['category_id'], 
                                      'page': meta['page'] + 1})
    
    def parse_detail(self, response):
        item = response.meta['item']
        detail = response.xpath('//*[@class="content-article"]//text()').extract()
        if detail:
            detail = [text for text in detail if text.strip() and text.strip() != '\n']
        else:
            detail = response.xpath('//*[@class="short-article"]//text()').extract()
            detail = [text for text in detail if text.strip() and text.strip() != '\n']
        item['detail'] = '\n'.join(detail)
        yield item