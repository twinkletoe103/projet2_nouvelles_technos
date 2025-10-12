from deep_translator import GoogleTranslator
import scrapy

class HlProjet2Spider(scrapy.Spider):
    name = "hl_projet2"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    compteur = 0
    max_items = 2500
    all_links = []  # pour stocker tous les liens scrappés
    index_loop = 0  # pour boucler sur les liens

    translator = GoogleTranslator(source="en", target="fr")
    cache_traductions = {}  # cache local pour accélérer

    # tarduction avec cache et gestion d'erreur
    def translate_text(self, texte):
        if not texte:
            return ""
        texte = texte.strip()
        if texte in self.cache_traductions:
            return self.cache_traductions[texte]
        try:
            traduction = self.translator.translate(texte)
            self.cache_traductions[texte] = traduction
            return traduction
        except Exception as e:
            # retour du texte original si problème
            self.logger.warning(f"Erreur de traduction pour '{texte}': {e}")
            return texte

    # va récupérer toutes les pages avant d'appeler scrape_loop, qui lui appelle parse_book pour ramasser les infos souhaitées
    def parse(self, response):
        links = response.css("h3 a::attr(href)").getall()
        links = [response.urljoin(l) for l in links]

        for link in links:
            if link not in self.all_links:
                self.all_links.append(link)

        # pagination, parce que tous les produits ne sont pas sur une seule page
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)
        else:
            # une fois tous les liens collectés, commence le scraping en boucle
            # yield from self.scrape_loop()
            if self.all_links:
                yield scrapy.Request(
                    self.all_links[self.index_loop],
                    callback=self.parse_book
                )

    def scrape_loop(self):
        # boucle sur les liens jusqu'à atteindre max_items
        while self.compteur < self.max_items:
            link = self.all_links[self.index_loop]
            self.index_loop = (self.index_loop + 1) % len(self.all_links)
            yield scrapy.Request(link, callback=self.parse_book)

    def parse_book(self, response):
        if self.compteur >= self.max_items:
            self.logger.info(f"Récolte de données complétée ({self.max_items} items collectés).")
            raise scrapy.exceptions.CloseSpider(reason="max_items_reached")

        self.compteur += 1

        reviews_text = response.css("table.table.table-striped tr:nth-child(7) td::text").get()
        try:
            nombre_revs = int(reviews_text.strip())
        except:
            nombre_revs = 0

        # catégorie et sous-catégorie pour permettre de filtre
        categories = response.css("ul.breadcrumb li a::text").getall()
        sous_categorie = categories[-1] if len(categories) >= 2 else ""

        # récupérer les données texte d'abord pour les traduire avant de les mettres dans le fichier json
        titre = response.css("div.product_main h1::text").get()
        disponibilite = response.css("p.availability::text").getall()[-1].strip()
        categorie = categories[1] if len(categories) >= 2 else ""

        # traduction des données texte
        titre = self.translate_text(titre)
        disponibilite = self.translate_text(disponibilite)
        categorie = self.translate_text(categorie)
        sous_categorie = self.translate_text(sous_categorie)

        # ajout des données dans le fichier json
        yield {
            "id_livre": self.compteur-1,
            "titre": titre,
            "prix": float(response.css("p.price_color::text").re_first(r"[\d\.]+")),
            "disponibilite": disponibilite,
            "categorie": categorie,
            "sous_categorie": sous_categorie,
            "nombre_revs": nombre_revs,
            "image_url": response.urljoin(response.css("div.item img::attr(src)").get()),
            "url": response.url
        }

        if self.compteur < self.max_items:
            self.index_loop = (self.index_loop + 1) % len(self.all_links)
            next_link = self.all_links[self.index_loop]
            yield scrapy.Request(next_link, callback=self.parse_book)