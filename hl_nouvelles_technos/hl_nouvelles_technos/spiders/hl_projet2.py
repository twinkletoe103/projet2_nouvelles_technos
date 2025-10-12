import scrapy

class HlProjet2Spider(scrapy.Spider):
    name = "hl_projet2"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    compteur = 0
    max_items = 2500
    all_links = []  # pour stocker tous les liens scrappés
    index_loop = 0  # pour boucler sur les liens

    def parse(self, response):
        # Stocke tous les liens de la page si ce n'est pas déjà fait
        links = response.css("h3 a::attr(href)").getall()
        links = [response.urljoin(l) for l in links]

        for link in links:
            if link not in self.all_links:
                self.all_links.append(link)

        # Pagination
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)
        else:
            # une fois tous les liens collectés, commence le scraping en boucle
            yield from self.scrape_loop()

    def scrape_loop(self):
        # Boucle sur les liens jusqu'à atteindre max_items
        while self.compteur < self.max_items:
            link = self.all_links[self.index_loop]
            self.index_loop = (self.index_loop + 1) % len(self.all_links)
            yield scrapy.Request(link, callback=self.parse_book)

    def parse_book(self, response):
        if self.compteur >= self.max_items:
            return

        self.compteur += 1

        # Nombre de revues
        reviews_text = response.css("table.table.table-striped tr:nth-child(7) td::text").get()
        try:
            nombre_revs = int(reviews_text.strip())
        except:
            nombre_revs = 0

        # Catégorie et sous-catégorie
        categories = response.css("ul.breadcrumb li a::text").getall()
        sous_categorie = categories[-1] if len(categories) >= 2 else ""

        yield {
            "id": self.compteur-1,
            "titre": response.css("div.product_main h1::text").get(),
            "prix": float(response.css("p.price_color::text").re_first(r"[\d\.]+")),
            "disponibilite": response.css("p.availability::text").getall()[-1].strip(),
            "categorie": categories[1] if len(categories) >= 2 else "",
            "sous_categorie": sous_categorie,
            "nombre_revs": nombre_revs,
            "image_url": response.urljoin(response.css("div.item img::attr(src)").get()),
            "url": response.url
        }
