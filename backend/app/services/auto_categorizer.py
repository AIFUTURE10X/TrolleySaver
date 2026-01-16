"""
Auto-Categorizer Service

Automatically categorizes products based on keyword matching in product names.
Maps products from Woolworths, Coles, ALDI, IGA to a unified category structure.
Supports both parent categories and subcategories for granular classification.

Features:
- Priority-based scoring to handle ambiguous matches
- Primary product detection to distinguish "Tuna in Sauce" from "Tomato Sauce"
- Descriptor pattern stripping to identify core product type
"""
import re
from typing import Optional, Tuple, List

# Category priority weights - higher number = higher priority when multiple matches
# Specific product categories beat generic descriptor categories
CATEGORY_PRIORITY = {
    # Specific product types (highest priority)
    "canned-food": 90,          # John West Tuna = canned food, not sauce
    "seafood": 85,              # Fresh seafood
    "beef-veal": 85,
    "chicken": 85,
    "pork": 85,
    "lamb": 85,
    "sausages-bbq": 80,
    "mince-burgers": 80,
    "frozen-meals": 75,
    "frozen-seafood": 75,
    "frozen-meat-poultry": 75,
    # Medium priority - specific categories
    "chips-crisps": 70,
    "biscuits": 70,
    "chocolate": 70,
    "milk": 70,
    "cheese": 70,
    "yoghurt": 70,
    "bread": 70,
    "pasta-noodles": 70,
    "rice-grains": 70,
    "soft-drinks": 70,
    "juice": 70,
    "water": 70,
    # Lower priority - categories often matched as descriptors
    "sauces-condiments": 40,    # "sauce" often appears in descriptors
    "breakfast-cereals": 50,
    # Parent categories (lowest priority - fallback)
    "meat-seafood": 30,
    "dairy-eggs-fridge": 30,
    "pantry": 20,
    "drinks": 20,
    "freezer": 20,
    "snacks-confectionery": 25,
    "bakery": 25,
}

# Descriptor patterns - these indicate secondary info, not primary product
# Used to strip descriptors before categorization for better matching
DESCRIPTOR_PATTERNS = [
    r"\s+in\s+\w+(\s+\w+)?\s+sauce",     # "in tomato sauce", "in onion savoury sauce"
    r"\s+in\s+(tomato|onion|oil|brine|springwater|water)",  # "in tomato", "in oil"
    r"\s+with\s+\w+(\s+&\s+\w+)?",        # "with corn", "with corn & mayo"
    r"\s+\w+\s+flavou?red?",              # "chicken flavoured"
    r"\s+style\s+\w+",                    # "Italian style"
    r"\s+\d+\s*(g|ml|l|kg|pk|pack)$",     # Size at end "95g", "500ml"
]

# Subcategory keywords mapping - maps to specific subcategory slugs
# These are checked FIRST to get the most specific category match
SUBCATEGORY_KEYWORDS = {
    # Meat & Seafood subcategories
    "beef-veal": {
        "keywords": ["beef", "veal", "steak", "rump", "scotch fillet", "porterhouse", "t-bone", "sirloin", "eye fillet", "brisket", "silverside", "corned beef", "beef roast", "beef strips"],
        "patterns": [r"beef\s+", r"veal\s+", r"angus", r"\bkg\b.*beef"],
        "exclude": ["beef flavour", "beef flavor", "beef stock", "beef broth", "beef noodle", "beef jerky", "twisties", "shapes", "chips", "crackers", "biscuit", "cup noodle", "instant noodle", "soup mix"],
    },
    "chicken": {
        "keywords": ["chicken breast", "chicken thigh", "chicken wing", "chicken drumstick", "chicken maryland", "chicken tenderloin", "chicken fillet", "chicken schnitzel", "whole chicken", "chicken pieces"],
        "patterns": [r"chicken\s+(breast|thigh|wing|drum|maryland|tender|fillet|schnitzel)", r"chook", r"\bkg\b.*chicken"],
        "exclude": ["chicken salt", "chicken flavour", "chicken flavor", "chicken stock", "chicken noodle", "chicken soup", "chicken cup", "chicken twisties", "chicken chips", "chicken crackers", "chicken crispy", "chicken seasoning", "rotisserie", "bbq chicken"],
    },
    "pork": {
        "keywords": ["pork chop", "pork loin", "pork belly", "pork roast", "pork mince", "pork steak", "pork fillet", "pork shoulder", "pork ribs", "pork cutlet", "pork scotch"],
        "patterns": [r"pork\s+(chop|loin|belly|roast|mince|steak|fillet|shoulder|rib|cutlet|scotch)", r"\bkg\b.*pork"],
        "exclude": ["pork crackling", "pork rind", "pork flavour", "pork flavor", "pork scratchings", "chips", "snack"],
    },
    "lamb": {
        "keywords": ["lamb chop", "lamb cutlet", "lamb leg", "lamb roast", "lamb shank", "lamb shoulder", "lamb rack", "lamb mince", "lamb loin", "lamb backstrap"],
        "patterns": [r"lamb\s+(chop|cutlet|leg|roast|shank|shoulder|rack|mince|loin|backstrap)", r"\bkg\b.*lamb"],
        "exclude": ["lamb flavour", "lamb flavor", "lamb stock", "lamb broth"],
    },
    "seafood": {
        "keywords": ["salmon fillet", "salmon portions", "tuna steak", "prawns", "king prawns", "tiger prawns", "shrimp", "barramundi", "snapper", "cod fillet", "hoki",
                    "flathead", "calamari", "squid", "octopus", "mussels", "oyster", "crab", "lobster", "scallop", "basa", "dory", "perch", "trout",
                    "whiting", "blue whiting", "ocean royale"],
        "patterns": [r"seafood", r"fish\s+fillet", r"(salmon|tuna|prawn|barramundi|snapper|whiting)\s+\d+g", r"fresh\s+(salmon|tuna|prawns|fish)", r"fillets?\s+\d+"],
        "exclude": ["fish oil", "fish sauce", "fish fingers", "fish crackers", "fish shaped", "goldfish", "fish stock", "tuna can", "canned tuna", "tinned"],
    },
    "mince-burgers": {
        "keywords": ["beef mince", "pork mince", "lamb mince", "chicken mince", "turkey mince", "burger patty", "beef patty", "patties", "rissole", "rissoles", "meat patty"],
        "patterns": [r"(beef|pork|lamb|chicken|turkey)\s+mince", r"mince\s+\d+g", r"burger\s+patty", r"patties\s+\d+"],
        "exclude": ["burger rings", "burger sauce", "burger seasoning", "burger buns", "burger cheese", "mince pie", "fruit mince"],
    },
    "sausages-bbq": {
        "keywords": ["sausage", "snag", "banger", "bratwurst", "kransky", "frankfurter", "wiener", "weiner", "cabanossi", "chipolata"],
        "patterns": [r"sausage", r"beef\s+sausage", r"pork\s+sausage", r"bbq\s+meat", r"bbq\s+pack"],
        "exclude": ["shapes", "chips", "pringles", "sauce", "rolls", "buns", "bread", "flavour", "flavor", "seasoning", "marinade", "rub", "cracker", "biscuit", "crisp", "snack", "ring", "twisties", "franklin", "water", "sparkling"],
    },
    "turkey-duck": {
        "keywords": ["turkey", "duck", "goose"],
        "patterns": [r"turkey\s+", r"duck\s+"],
    },

    # Dairy subcategories
    "milk": {
        "keywords": ["full cream milk", "skim milk", "lite milk", "lactose free milk", "almond milk", "oat milk", "soy milk", "fresh milk", "long life milk", "uht milk", "a2 milk", "jersey milk"],
        "patterns": [r"\d+\s*l(itre)?.*milk", r"milk\s+\d+\s*l", r"(pauls|pura|dairy farmers|devondale|so good).*milk"],
        "exclude": ["milk chocolate", "milky bar", "milky way", "milk bottle", "milk biscuit", "condensed milk", "evaporated milk", "coconut milk", "milk powder"],
    },
    "cheese": {
        "keywords": ["cheddar cheese", "tasty cheese", "mozzarella cheese", "parmesan cheese", "brie cheese", "camembert", "feta cheese", "haloumi", "gouda cheese", "swiss cheese", "cream cheese", "cottage cheese", "ricotta", "cheese slices", "cheese block", "shredded cheese"],
        "patterns": [r"cheese\s+\d+g", r"cheese\s+slices", r"(bega|kraft|coon|mainland|philadelphia).*cheese", r"slices\s+\d+\s*pk"],
        "exclude": ["cheese crackers", "cheese shapes", "cheetos", "cheese twisties", "cheese & onion", "cheese flavour", "cheese flavor", "cheese rings", "cheeseburger", "mac & cheese", "mac and cheese", "nacho cheese"],
    },
    "yoghurt": {
        "keywords": ["yoghurt", "yogurt", "greek yoghurt", "natural yoghurt", "chobani", "yoplait", "activia", "vaalia", "jalna", "farmers union", "siggi's"],
        "patterns": [r"yogh?urt\s+\d+", r"(chobani|yoplait|vaalia|jalna)"],
        "exclude": ["yoghurt coating", "yoghurt covered", "yoghurt drops", "frozen yoghurt", "frozen yogurt"],
    },
    "eggs": {
        "keywords": ["free range eggs", "cage free eggs", "dozen eggs", "barn laid eggs", "organic eggs", "large eggs", "extra large eggs", "jumbo eggs"],
        "patterns": [r"\d+\s*eggs?\s*(dozen|pk|pack)", r"eggs?\s+\d+\s*pk", r"(farm|barn|free range|cage free).*eggs"],
        "exclude": ["egg noodles", "easter egg", "scotch egg", "egg custard", "egg tart", "chocolate egg", "egg wash", "egg replacer"],
    },
    "butter-cream": {
        "keywords": ["salted butter", "unsalted butter", "spreadable butter", "margarine", "thickened cream", "pure cream", "sour cream", "cooking cream", "double cream", "light cream"],
        "patterns": [r"butter\s+\d+g", r"cream\s+\d+ml", r"(devondale|mainland|western star|flora|nuttelex).*butter"],
        "exclude": ["ice cream", "cream biscuit", "cream cheese", "butter chicken", "peanut butter", "body butter", "cocoa butter", "shea butter", "cream puff", "cream filling", "cookies & cream", "cookies and cream"],
    },

    # Drinks subcategories
    "soft-drinks": {
        "keywords": ["coca-cola", "coca cola", "coke", "pepsi", "sprite", "fanta", "solo", "lift", "sunkist", "schweppes", "lemonade", "soft drink", "kirks", "bundaberg"],
        "patterns": [r"(coca|pepsi|sprite|fanta|solo|kirks|schweppes).*\d+\s*(ml|l|pack)", r"soft\s+drink"],
        "exclude": ["coke zero sugar snack", "lemonade scone"],
    },
    "water": {
        "keywords": ["spring water", "mineral water", "sparkling water", "still water", "purified water", "alkaline water", "bottled water", "san pellegrino", "evian", "pump water", "mount franklin"],
        "patterns": [r"water\s+\d+\s*(ml|l|pack)", r"\d+\s*(ml|l).*water", r"(mount franklin|pump|evian|voss)"],
        "exclude": ["coconut water", "rose water", "rice water", "micellar water", "tonic water", "soda water"],
    },
    "juice": {
        "keywords": ["orange juice", "apple juice", "fruit juice", "vegetable juice", "tomato juice", "cranberry juice", "grape juice", "pineapple juice", "mango juice", "nudie", "daily juice", "berri"],
        "patterns": [r"juice\s+\d+\s*(ml|l)", r"\d+\s*(ml|l).*juice", r"(nudie|berri|golden circle).*juice"],
        "exclude": ["juice bar", "vape juice", "e-juice"],
    },
    "coffee-tea": {
        "keywords": ["instant coffee", "ground coffee", "coffee beans", "coffee capsules", "coffee pods", "tea bags", "green tea", "herbal tea", "black tea", "nescafe", "moccona", "lavazza", "vittoria", "twinings", "lipton", "t2"],
        "patterns": [r"coffee\s+\d+g", r"tea\s+\d+\s*(bag|pk)", r"(nescafe|moccona|lavazza|vittoria)"],
        "exclude": ["coffee table", "coffee mug", "coffee cup", "iced coffee", "coffee milk"],
    },
    "energy-drinks": {
        "keywords": ["energy drink", "red bull", "v energy", "mother energy", "monster energy", "rockstar", "nos", "prime energy"],
        "patterns": [r"energy\s+drink", r"(red bull|mother|monster|rockstar).*\d+\s*(ml|pack)"],
        "exclude": ["energy bar", "energy ball", "energy bites"],
    },

    # Pantry subcategories
    "pasta-noodles": {
        "keywords": ["dried pasta", "spaghetti", "penne", "fettuccine", "linguine", "fusilli", "rigatoni", "lasagne sheets", "egg noodles", "rice noodles", "ramen noodles", "udon", "san remo", "barilla"],
        "patterns": [r"pasta\s+\d+g", r"noodles?\s+\d+g", r"(san remo|barilla|la zara)"],
        "exclude": ["pasta sauce", "pasta bake", "fresh pasta", "pasta salad"],
    },
    "rice-grains": {
        "keywords": ["basmati rice", "jasmine rice", "brown rice", "white rice", "long grain rice", "arborio rice", "quinoa", "couscous", "bulgur", "pearl barley", "sunrice", "ben's original"],
        "patterns": [r"rice\s+\d+\s*(g|kg)", r"(sunrice|ben's original|uncle ben)"],
        "exclude": ["rice crackers", "rice cakes", "rice paper", "rice noodles", "rice pudding", "rice bran oil", "rice flour"],
    },
    "canned-food": {
        "keywords": [
            "canned tomatoes", "diced tomatoes", "crushed tomatoes",
            "canned tuna", "canned salmon", "baked beans",
            "canned corn", "canned beetroot", "chickpeas", "kidney beans",
            "black beans", "lentils", "spc", "edgell", "heinz beans",
            # Canned tuna/seafood brands - these are ALWAYS canned products
            "john west", "sirena", "safcol", "greenseas",
        ],
        "patterns": [
            r"(john west|sirena|safcol|greenseas)\s+\w+",  # Tuna brands
            r"(canned|tinned)\s+\w+",
            r"\d+g\s*(can|tin)",
            r"(spc|edgell|annalisa).*\d+g",
            r"tuna\s+(in|with)\s+",  # "Tuna in tomato", "Tuna with corn"
        ],
        "exclude": ["can opener", "garbage can", "tuna steak", "fresh tuna", "sashimi"],
    },
    "sauces-condiments": {
        "keywords": ["tomato sauce", "bbq sauce", "barbecue sauce", "soy sauce", "worcestershire",
                     "ketchup", "mustard", "relish", "aioli", "hot sauce", "chilli sauce",
                     "sweet chilli sauce", "sriracha", "tabasco", "masterfoods sauce", "fountain sauce"],
        "patterns": [
            r"(tomato|bbq|soy|worcester|chilli|hot|sweet chilli|teriyaki|oyster)\s+sauce\s+\d+",
            r"(heinz|masterfoods|fountain|rosella).*sauce\s+\d+",
            r"ketchup\s+\d+",
            r"mayonnaise\s+\d+",
        ],
        "exclude": [
            # Seafood products with sauce descriptors
            "tuna", "john west", "salmon", "sardine", "mackerel", "anchovies", "sirena", "safcol", "greenseas",
            # Meat products
            "chicken", "beef", "pork", "lamb",
            # Descriptor patterns (product IN sauce, not sauce itself)
            "in sauce", "with sauce", "in tomato", "in onion", "in oil", "in brine", "in springwater",
            "& mayonnaise", "with mayonnaise", "with corn", "with chilli", "with sweet",
            # Cooking sauces (different category)
            "pasta sauce", "simmer sauce", "cooking sauce", "stir fry sauce", "curry sauce", "satay sauce",
            "soup", "casserole",
        ],
    },
    "breakfast-cereals": {
        "keywords": ["weet-bix", "weetbix", "cornflakes", "nutri-grain", "muesli", "granola", "rolled oats", "porridge", "special k", "coco pops", "froot loops", "cheerios", "all bran", "just right", "sultana bran"],
        "patterns": [r"cereal\s+\d+g", r"breakfast\s+cereal", r"(kellogg|sanitarium|uncle tobys)"],
        "exclude": ["cereal bar", "breakfast bar"],
    },

    # Snacks subcategories
    "chips-crisps": {
        "keywords": ["potato chips", "corn chips", "tortilla chips", "smiths chips", "thins", "pringles", "doritos", "kettle chips", "red rock deli", "twisties", "cheezels", "burger rings", "cheetos", "grain waves", "cc's", "samboy", "vege chips"],
        "patterns": [r"chips\s+\d+g", r"crisps\s+\d+g", r"(smiths|kettle|doritos|pringles|red rock|twisties|cheezels)"],
        "exclude": ["fish and chips", "fish & chips", "frozen chips", "oven chips", "hot chips"],
    },
    "chocolate": {
        "keywords": ["chocolate block", "chocolate bar", "cadbury", "lindt", "ferrero rocher", "mars bar", "snickers", "twix", "kit kat", "toblerone", "maltesers", "m&m", "bounty", "milky way", "picnic", "crunchie", "cherry ripe", "boost", "kinder"],
        "patterns": [r"chocolate\s+\d+g", r"(cadbury|lindt|nestle|ferrero).*\d+g", r"choc\s+\d+g"],
        "exclude": ["chocolate milk", "hot chocolate", "chocolate spread", "chocolate sauce", "chocolate chip", "chocolate flavour", "chocolate flavor"],
    },
    "biscuits": {
        "keywords": ["tim tam", "oreo", "arnott's", "arnotts", "shapes", "scotch finger", "monte carlo", "shortbread", "anzac biscuit", "digestive", "nice biscuit", "cream biscuit", "chocolate biscuit", "teddy bear biscuit", "tiny teddy", "iced vovo", "kingston", "delta cream"],
        "patterns": [r"biscuit\s+\d+g", r"cookies?\s+\d+g", r"(arnott|tim tam|oreo|shapes)"],
        "exclude": ["dog biscuit", "cat biscuit", "pet biscuit"],
    },
    "lollies": {
        "keywords": ["lollies", "candy", "gummy bears", "gummy worms", "jelly beans", "licorice", "allsorts", "snakes", "party mix", "sour worms", "sour straps", "mentos", "skittles", "starburst", "lifesavers", "tic tac", "minties", "fantales", "redskins", "milkos"],
        "patterns": [r"lollies\s+\d+g", r"candy\s+\d+g", r"(haribo|allen|darrell lea)"],
        "exclude": ["lollipop stick", "lolly bag"],
    },
    "nuts-snacks": {
        "keywords": ["roasted peanuts", "salted peanuts", "almonds", "cashews", "macadamia nuts", "walnuts", "pistachios", "mixed nuts", "trail mix", "beer nuts", "honey roasted peanuts", "salted cashews"],
        "patterns": [r"nuts\s+\d+g", r"(roasted|salted|honey)\s+(peanuts|almonds|cashews|macadamia)", r"(cobram|forresters).*nuts"],
        "exclude": ["coconut", "doughnut", "donut", "hazelnut spread", "nutella"],
    },

    # Freezer subcategories
    "ice-cream-frozen-desserts": {
        "keywords": ["ice cream", "gelato", "sorbet", "frozen yogurt", "magnum", "cornetto", "paddle pop", "streets", "peters", "connoisseur", "ben & jerry", "haagen dazs", "bulla", "weis bar", "zooper dooper", "calippo", "gaytime"],
        "patterns": [r"ice\s*cream\s+\d+", r"(streets|peters|bulla|connoisseur).*\d+"],
        "exclude": ["ice cream cone", "ice cream scoop", "ice cream maker"],
    },
    "frozen-meals": {
        "keywords": ["frozen meal", "ready meal", "tv dinner", "lean cuisine", "healthy choice", "weight watchers meal", "on the menu", "youfoodz"],
        "patterns": [r"frozen\s+meal", r"ready\s+meal", r"(lean cuisine|healthy choice|on the menu)"],
        "exclude": ["meal kit", "meal prep container"],
    },
    "frozen-vegetables": {
        "keywords": ["frozen peas", "frozen corn", "frozen vegetables", "frozen beans", "frozen spinach", "frozen broccoli", "frozen stir fry vegetables", "frozen mixed vegetables", "birds eye vegetables", "mccain vegetables"],
        "patterns": [r"frozen\s+(pea|corn|veg|bean|spinach|broccoli|carrot)", r"(birds eye|mccain).*vegetables"],
    },
    "frozen-chips-wedges": {
        "keywords": ["frozen chips", "oven chips", "potato wedges", "hash browns", "potato gems", "frozen crinkle cut", "frozen straight cut", "steakhouse chips", "mccain chips", "birds eye chips"],
        "patterns": [r"frozen\s+chips?", r"oven\s+chips?", r"(mccain|birds eye).*chips", r"hash\s*brown"],
        "exclude": ["fish and chips meal", "cheese & onion", "cheese and onion", "sour cream", "salt & vinegar", "chicken", "bbq", "smiths", "thins", "pringles", "sprinters"],
    },

    # Cleaning subcategories
    "laundry": {
        "keywords": ["laundry", "washing powder", "fabric softener", "stain remover", "omo", "cold power", "dynamo", "napisan"],
        "patterns": [r"laundry\s+", r"washing\s+powder"],
    },
    "dishwashing": {
        "keywords": ["dishwashing", "dish soap", "dishwasher tablets", "rinse aid", "finish", "fairy", "morning fresh"],
        "patterns": [r"dishwash", r"dish\s+"],
    },
    "cleaning-products": {
        "keywords": ["surface spray", "bathroom cleaner", "kitchen cleaner", "glass cleaner", "floor cleaner", "ajax", "windex", "mr muscle"],
        "patterns": [r"cleaner\s+", r"spray\s+\d+"],
    },
    "paper-products": {
        "keywords": ["toilet paper", "paper towel", "tissues", "kleenex", "sorbent", "quilton"],
        "patterns": [r"toilet\s+paper", r"paper\s+towel"],
    },

    # Personal care subcategories
    "hair-care": {
        "keywords": ["shampoo", "conditioner", "hair treatment", "hair mask", "hair gel", "hair spray", "head & shoulders", "pantene", "tresemme"],
        "patterns": [r"shampoo", r"conditioner"],
    },
    "body-wash-soap": {
        "keywords": ["body wash", "soap", "shower gel", "bath", "dove", "palmolive"],
        "patterns": [r"body\s+wash", r"shower\s+gel"],
    },
    "deodorant": {
        "keywords": ["deodorant", "antiperspirant", "roll on", "rexona", "lynx", "dove deo", "nivea deo"],
        "patterns": [r"deodorant", r"antiperspirant"],
    },
    "oral-care": {
        "keywords": ["toothpaste", "toothbrush", "mouthwash", "dental", "colgate", "oral-b", "sensodyne", "listerine"],
        "patterns": [r"toothpaste", r"toothbrush", r"mouthwash"],
    },

    # ==========================================
    # NEW SUBCATEGORY DEFINITIONS
    # ==========================================

    # Fruit & Veg subcategories
    "fresh-fruit": {
        "keywords": ["fresh apple", "fresh banana", "fresh orange", "fresh mandarin", "fresh grapes", "fresh strawberries", "fresh blueberries", "fresh raspberries", "fresh mango", "fresh pineapple", "watermelon", "rockmelon", "honeydew", "fresh pear", "fresh peach", "nectarine", "fresh plum", "fresh kiwi", "fresh avocado", "passionfruit", "papaya", "pink lady apple", "granny smith", "royal gala"],
        "patterns": [r"fresh\s+(apple|banana|orange|grape|strawberr|mango|pear)", r"australian\s+(mango|peach|grape|apple)", r"(gala|fuji|pink lady)\s+apple"],
        "exclude": ["apple juice", "banana bread", "orange juice", "dried fruit", "fruit bar", "fruit snack", "juice", "pulp", "cordial", "ham", "spiced", "canned", "labeller", "blue ", "dymo"],
    },
    "fresh-vegetables": {
        "keywords": ["fresh broccoli", "fresh carrot", "fresh potato", "fresh onion", "fresh tomato", "fresh lettuce", "fresh spinach", "fresh kale", "fresh cabbage", "fresh cauliflower", "fresh capsicum", "fresh cucumber", "fresh zucchini", "fresh eggplant", "fresh mushroom", "fresh celery", "fresh asparagus", "fresh beetroot", "fresh pumpkin", "sweet potato", "loose carrots", "loose potatoes", "loose onions"],
        "patterns": [r"fresh\s+(broccoli|carrot|potato|onion|tomato|lettuce)", r"baby\s+(spinach|carrots|corn)", r"bunch\s+(celery|asparagus)", r"(woolworths|coles)\s+(carrot|potato|onion|tomato)"],
        "exclude": ["frozen", "canned", "tinned", "chips", "sauce", "popcorn", "corn chips", "sweet corn"],
    },
    "salad": {
        "keywords": ["salad mix", "salad bag", "coleslaw mix", "salad kit", "caesar salad", "garden salad", "rocket salad", "baby spinach salad", "mixed leaves"],
        "patterns": [r"salad\s+(mix|bag|kit|bowl)", r"mixed\s+leaves"],
        "exclude": ["salad dressing", "pasta salad", "potato salad"],
    },
    "prepared-vegetables": {
        "keywords": ["stir fry vegetables", "vegetable medley", "pre-cut vegetables", "diced vegetables", "sliced vegetables", "vegetable tray", "party platter vegetables"],
        "patterns": [r"(stir fry|cut|diced|sliced)\s+veg", r"veg.*medley"],
    },
    "organic-produce": {
        "keywords": ["organic apple", "organic banana", "organic carrot", "organic spinach", "organic tomato", "organic avocado", "certified organic"],
        "patterns": [r"organic\s+(apple|banana|carrot|spinach|tomato|veg|fruit)"],
    },
    "herbs-garlic-chillies": {
        "keywords": ["fresh basil", "fresh parsley", "fresh coriander", "fresh mint", "fresh rosemary", "fresh thyme", "garlic bulb", "fresh ginger", "fresh chilli", "spring onion", "shallot", "lemongrass"],
        "patterns": [r"fresh\s+(basil|parsley|coriander|mint|rosemary|thyme|dill|ginger|chilli)", r"garlic\s+bulb"],
        "exclude": ["garlic bread", "garlic sauce", "dried herbs", "ginger cookies", "ginger biscuit", "ginger beer", "ginger ale", "ginger nut", "chilli sauce", "chilli oil", "chilli flakes", "sweet chilli", "chilli con", "chilli powder"],
    },

    # Deli subcategories
    "cold-cuts-salami": {
        "keywords": ["sliced ham", "leg ham", "salami", "prosciutto", "pastrami", "mortadella", "pepperoni", "chorizo slices", "ham off the bone", "smoked salmon slices"],
        "patterns": [r"sliced\s+(ham|salami|turkey|chicken)", r"(don|primo|hans).*sliced"],
    },
    "deli-cheese": {
        "keywords": ["deli brie", "deli camembert", "deli blue cheese", "deli gouda", "deli gruyere", "specialty cheese", "cheese wheel"],
        "patterns": [r"deli\s+cheese", r"specialty\s+cheese"],
    },
    "olives-antipasto": {
        "keywords": ["kalamata olives", "green olives", "stuffed olives", "marinated olives", "sundried tomatoes", "antipasto platter", "chargrilled vegetables", "marinated artichokes", "marinated feta"],
        "patterns": [r"(kalamata|green|stuffed|marinated)\s+olives", r"antipasto"],
    },
    "dips-spreads": {
        "keywords": ["hummus", "tzatziki", "guacamole", "beetroot dip", "french onion dip", "spinach dip", "basil pesto", "tapenade", "baba ganoush"],
        "patterns": [r"(hummus|tzatziki|guacamole|pesto)\s*\d*g", r"(beetroot|french onion|spinach)\s+dip"],
        "exclude": ["chip dip", "sauce"],
    },
    "cooked-meats": {
        "keywords": ["rotisserie chicken", "roast chicken", "bbq chicken", "roast beef", "roast pork", "roast lamb", "hot roast"],
        "patterns": [r"(rotisserie|roast|bbq)\s+(chicken|beef|pork|lamb)"],
        "exclude": ["roast chicken flavour", "roast beef flavour"],
    },

    # Dairy additional subcategories
    "cream-custard": {
        "keywords": ["custard", "vanilla custard", "chocolate custard", "caramel custard", "paul's custard", "dairy dessert", "rice pudding"],
        "patterns": [r"custard\s+\d+", r"(paul|dairy farmers).*custard"],
        "exclude": ["custard powder", "custard tart"],
    },
    "chilled-desserts": {
        "keywords": ["cheesecake", "mousse", "tiramisu", "panna cotta", "creme brulee", "chilled dessert", "chocolate mousse", "mango mousse"],
        "patterns": [r"(cheesecake|mousse|tiramisu|panna cotta)\s*\d*g"],
        "exclude": ["cheesecake mix", "mousse powder"],
    },

    # Bakery subcategories
    "bread": {
        "keywords": ["white bread", "wholemeal bread", "multigrain bread", "sourdough bread", "rye bread", "sliced bread", "bread loaf", "sandwich bread", "tip top bread", "helga's bread", "wonder white"],
        "patterns": [r"(white|wholemeal|multigrain|sourdough|rye)\s+bread", r"bread\s+\d+g", r"(tip top|helga|abbott|wonder white)"],
        "exclude": ["bread crumbs", "bread mix"],
    },
    "bread-rolls-wraps": {
        "keywords": ["bread rolls", "dinner rolls", "burger buns", "hot dog rolls", "hot dog buns", "brioche buns", "wraps", "tortilla wraps", "pita bread", "naan bread", "flatbread", "lebanese bread", "mountain bread"],
        "patterns": [r"(bread|dinner|burger|hot dog)\s+(roll|bun)", r"(tortilla|pita|naan|flatbread)\s*\d*"],
        "exclude": ["sausage roll", "spring roll"],
    },
    "cakes-tarts": {
        "keywords": ["chocolate cake", "sponge cake", "mud cake", "cheesecake", "carrot cake", "fruit cake", "apple tart", "custard tart", "lemon tart", "fruit tart"],
        "patterns": [r"(chocolate|sponge|mud|carrot|fruit)\s+cake", r"(apple|custard|lemon|fruit)\s+tart"],
    },
    "pastries-croissants": {
        "keywords": ["croissant", "danish pastry", "pain au chocolat", "almond croissant", "butter croissant", "apple turnover", "custard danish", "cinnamon scroll"],
        "patterns": [r"croissant\s*\d*", r"danish\s+pastry", r"(pain au chocolat|turnover|scroll)"],
    },
    "muffins-donuts": {
        "keywords": ["chocolate muffin", "blueberry muffin", "banana muffin", "bran muffin", "donut", "doughnut", "cinnamon donut", "glazed donut", "jam donut"],
        "patterns": [r"(chocolate|blueberry|banana|bran)\s+muffin", r"(cinnamon|glazed|jam)\s+donut"],
    },
    "gluten-free-bakery": {
        "keywords": ["gluten free bread", "gluten free wraps", "gluten free muffin", "gluten free cake", "gluten free rolls"],
        "patterns": [r"gluten\s+free\s+(bread|wrap|muffin|cake|roll)"],
    },

    # Pantry additional subcategories
    "cooking-oils": {
        "keywords": ["olive oil", "extra virgin olive oil", "vegetable oil", "canola oil", "sunflower oil", "coconut oil", "avocado oil", "peanut oil", "sesame oil"],
        "patterns": [r"(olive|vegetable|canola|sunflower|coconut|avocado)\s+oil\s*\d*"],
        "exclude": ["oil spray", "fish oil"],
    },
    "spreads-honey": {
        "keywords": ["honey", "manuka honey", "jam", "strawberry jam", "apricot jam", "peanut butter", "vegemite", "nutella", "hazelnut spread", "marmalade", "lemon curd", "maple syrup", "golden syrup", "treacle"],
        "patterns": [r"(strawberry|apricot|raspberry)\s+jam", r"(peanut|almond|cashew)\s+butter", r"honey\s+\d+g", r"maple\s+syrup"],
        "exclude": ["honey chicken", "honey soy"],
    },
    "baking-supplies": {
        "keywords": ["flour", "plain flour", "self raising flour", "sugar", "caster sugar", "brown sugar", "icing sugar", "baking powder", "baking soda", "bicarbonate", "yeast", "vanilla essence", "chocolate chips", "cocoa powder"],
        "patterns": [r"(plain|self raising|bread)\s+flour", r"(caster|brown|icing)\s+sugar", r"baking\s+(powder|soda)"],
    },
    "herbs-spices": {
        "keywords": ["dried basil", "dried oregano", "dried thyme", "paprika", "cumin", "turmeric", "cinnamon", "nutmeg", "black pepper", "sea salt", "garlic powder", "onion powder", "mixed herbs", "italian herbs"],
        "patterns": [r"(paprika|cumin|turmeric|cinnamon|nutmeg)\s*\d*g", r"(garlic|onion)\s+powder"],
        "exclude": ["fresh herbs"],
    },

    # Drinks additional subcategories
    "cordial-mixers": {
        "keywords": ["cordial", "lime cordial", "lemon cordial", "orange cordial", "tonic water", "soda water", "dry ginger ale", "lemon lime bitters"],
        "patterns": [r"(lime|lemon|orange)\s+cordial", r"(tonic|soda)\s+water"],
    },
    "sports-drinks": {
        "keywords": ["gatorade", "powerade", "maximus", "hydralyte", "electrolyte drink", "sports drink"],
        "patterns": [r"(gatorade|powerade|maximus)\s*\d*ml", r"electrolyte\s+(drink|powder)"],
    },

    # Freezer additional subcategories
    "frozen-seafood": {
        "keywords": ["frozen prawns", "frozen fish", "frozen salmon", "frozen basa", "fish fingers", "crumbed fish", "frozen calamari", "frozen squid"],
        "patterns": [r"frozen\s+(prawns|fish|salmon|basa|calamari)", r"fish\s+fingers"],
    },
    "frozen-meat-poultry": {
        "keywords": ["frozen chicken", "frozen beef", "frozen mince", "frozen sausages", "frozen burgers", "chicken nuggets", "chicken tenders"],
        "patterns": [r"frozen\s+(chicken|beef|mince|sausage|burger)", r"chicken\s+(nuggets|tenders|strips)"],
    },
    "frozen-pizza": {
        "keywords": ["frozen pizza", "mccain pizza", "dr oetker pizza", "pizza base", "pizza pocket"],
        "patterns": [r"frozen\s+pizza", r"(mccain|dr oetker).*pizza"],
        "exclude": ["pizza sauce", "pizza seasoning"],
    },
    "frozen-pastry": {
        "keywords": ["sausage roll", "meat pie", "party pie", "beef pie", "chicken pie", "spring roll", "dim sim", "samosa", "puff pastry", "shortcrust pastry", "filo pastry"],
        "patterns": [r"(sausage|meat|party|beef|chicken)\s+(roll|pie)", r"(spring roll|dim sim|samosa)\s*\d*"],
    },

    # Snacks additional subcategories
    "popcorn-pretzels": {
        "keywords": ["popcorn", "microwave popcorn", "butter popcorn", "caramel popcorn", "cobs popcorn", "pretzels", "pretzel twists", "rice crackers", "rice snacks"],
        "patterns": [r"(butter|caramel|microwave|salted|sweet)\s+popcorn", r"popcorn\s+\d+g", r"cobs.*popcorn", r"pretzel\s*\d*g", r"rice\s+cracker"],
    },
    "muesli-snack-bars": {
        "keywords": ["muesli bar", "nut bar", "protein bar", "fruit bar", "breakfast bar", "carman's bar", "be natural bar", "uncle toby's bar"],
        "patterns": [r"(muesli|nut|protein|fruit|breakfast)\s+bar", r"(carman|be natural|uncle toby)"],
    },

    # International subcategories
    "asian-foods": {
        "keywords": ["soy sauce", "teriyaki sauce", "hoisin sauce", "oyster sauce", "fish sauce", "rice paper", "rice noodles", "wonton wrappers", "tofu", "tempeh", "miso paste", "curry paste", "coconut milk"],
        "patterns": [r"(soy|teriyaki|hoisin|oyster|fish)\s+sauce", r"(rice|wonton)\s+(paper|wrapper|noodle)", r"(miso|curry)\s+paste"],
    },
    "mexican-foods": {
        "keywords": ["taco shells", "taco kit", "tortilla chips", "salsa", "guacamole", "refried beans", "burrito kit", "enchilada sauce", "nacho cheese", "jalapeno"],
        "patterns": [r"(taco|burrito|enchilada)\s+(shell|kit|sauce)", r"tortilla\s+chips"],
    },
    "indian-foods": {
        "keywords": ["curry paste", "tikka masala", "butter chicken sauce", "korma", "vindaloo", "naan bread", "poppadoms", "mango chutney", "lime pickle", "basmati rice"],
        "patterns": [r"(tikka|butter chicken|korma|vindaloo|rogan josh)\s*(sauce|paste)?", r"(naan|poppadom|papadum)"],
    },
    "italian-foods": {
        "keywords": ["pasta sauce", "bolognese sauce", "napolitana sauce", "pesto", "pizza sauce", "sun dried tomatoes", "balsamic vinegar", "risotto rice", "arborio rice", "parmesan"],
        "patterns": [r"(bolognese|napolitana|arrabbiata|puttanesca)\s+sauce", r"(balsamic|red wine)\s+vinegar"],
    },
    "middle-eastern-foods": {
        "keywords": ["hummus", "tahini", "falafel", "za'atar", "dukkah", "harissa", "pomegranate molasses", "lebanese bread", "pita chips"],
        "patterns": [r"(hummus|tahini|falafel|dukkah|harissa)\s*\d*g", r"za'atar"],
    },
    "european-foods": {
        "keywords": ["sauerkraut", "pierogi", "bratwurst", "german mustard", "polish sausage", "greek feta", "dolmades", "tzatziki"],
        "patterns": [r"(sauerkraut|pierogi|bratwurst|dolmades)"],
    },

    # Liquor additional subcategory
    "non-alcoholic-drinks": {
        "keywords": ["non alcoholic beer", "non alcoholic wine", "alcohol free beer", "alcohol free wine", "zero alcohol", "0% alcohol"],
        "patterns": [r"(non alcoholic|alcohol free|zero alcohol|0%)\s+(beer|wine|cider)"],
    },

    # Beauty subcategories
    "skincare": {
        "keywords": ["face wash", "cleanser", "moisturiser", "moisturizer", "face cream", "serum", "eye cream", "face mask", "exfoliator", "toner", "micellar water"],
        "patterns": [r"(face|facial)\s+(wash|cleanser|cream|mask|scrub)", r"(olay|neutrogena|garnier|l'oreal|loreal).*face"],
    },
    "makeup-cosmetics": {
        "keywords": ["foundation", "concealer", "mascara", "lipstick", "lip gloss", "eyeshadow", "eyeliner", "blush", "bronzer", "primer", "setting spray", "makeup remover"],
        "patterns": [r"(maybelline|revlon|rimmel|covergirl)\s+", r"(foundation|mascara|lipstick|eyeshadow)\s*\d*"],
    },
    "suncare": {
        "keywords": ["sunscreen", "sunblock", "spf", "sun lotion", "after sun", "tan lotion", "tanning", "cancer council"],
        "patterns": [r"sunscreen\s+spf", r"spf\s*\d+", r"(cancer council|banana boat|nivea sun)"],
    },
    "fragrance": {
        "keywords": ["perfume", "cologne", "eau de toilette", "eau de parfum", "body spray", "body mist", "aftershave"],
        "patterns": [r"(eau de|body)\s+(toilette|parfum|spray|mist)", r"(perfume|cologne|aftershave)\s*\d*ml"],
    },

    # Personal Care additional subcategories
    "shaving-hair-removal": {
        "keywords": ["razor", "razor blades", "shaving cream", "shaving gel", "shaving foam", "aftershave", "wax strips", "hair removal cream", "epilator", "electric shaver"],
        "patterns": [r"(gillette|schick|bic)\s+razor", r"shaving\s+(cream|gel|foam)", r"wax\s+strips"],
    },
    "feminine-care": {
        "keywords": ["tampons", "pads", "sanitary pads", "panty liners", "feminine wash", "period underwear", "libra", "carefree", "u by kotex"],
        "patterns": [r"(tampons|pads|liners)\s*\d*", r"(libra|carefree|kotex)"],
    },

    # Health additional subcategories
    "pain-relief": {
        "keywords": ["panadol", "nurofen", "paracetamol", "ibuprofen", "aspirin", "pain relief", "headache tablets", "deep heat", "voltaren", "tiger balm"],
        "patterns": [r"(panadol|nurofen|paracetamol|ibuprofen|aspirin)\s*\d*", r"pain\s+relief"],
    },
    "cold-flu": {
        "keywords": ["cold and flu", "cough syrup", "cough medicine", "throat lozenges", "strepsils", "butter menthol", "vicks", "nasal spray", "decongestant", "codral", "lemsip"],
        "patterns": [r"(cold|flu)\s+(tablet|capsule|liquid)", r"(strepsils|vicks|codral|lemsip)"],
    },
    "digestive-health": {
        "keywords": ["antacid", "gaviscon", "mylanta", "quick eze", "probiotics", "inner health", "yakult", "metamucil", "fibre supplement", "laxative"],
        "patterns": [r"(gaviscon|mylanta|quick eze|metamucil)\s*\d*", r"probiotic\s*\d*"],
    },

    # Cleaning additional subcategories
    "air-fresheners": {
        "keywords": ["air freshener", "room spray", "glade", "febreze", "airwick", "scented candle", "reed diffuser", "car freshener", "odour eliminator"],
        "patterns": [r"air\s+freshener", r"(glade|febreze|airwick)\s*", r"scented\s+candle"],
    },
    "pest-control": {
        "keywords": ["insect spray", "fly spray", "ant bait", "cockroach bait", "mosquito repellent", "mortein", "raid", "baygon", "mouse trap", "rat bait"],
        "patterns": [r"(insect|fly|bug)\s+spray", r"(ant|cockroach|mouse|rat)\s+(bait|trap)", r"(mortein|raid|baygon)"],
    },
    "batteries-electricals": {
        "keywords": ["batteries", "aa batteries", "aaa batteries", "9v battery", "duracell", "energizer", "light bulb", "led bulb", "extension cord", "power board"],
        "patterns": [r"(aa|aaa|9v|c|d)\s*batteries", r"(duracell|energizer)\s*\d*pk", r"(light|led)\s+bulb"],
    },

    # Baby additional subcategories
    "baby-food": {
        "keywords": ["baby puree", "baby food pouch", "baby cereal", "baby snacks", "baby rusks", "heinz baby", "rafferty's garden", "only organic baby"],
        "patterns": [r"baby\s+(puree|food|cereal|snack|rusk)", r"(heinz|rafferty|only organic).*baby"],
    },
    "baby-formula": {
        "keywords": ["infant formula", "baby formula", "toddler milk", "aptamil", "s26", "karicare", "nan", "a2 platinum"],
        "patterns": [r"(infant|baby|toddler)\s+(formula|milk)", r"(aptamil|s26|karicare|nan)\s*\d*"],
    },
    "baby-care": {
        "keywords": ["baby wash", "baby shampoo", "baby lotion", "nappy cream", "sudocrem", "baby powder", "baby oil", "nappy bags"],
        "patterns": [r"baby\s+(wash|shampoo|lotion|powder|oil)", r"nappy\s+(cream|bag)"],
    },

    # Pet additional subcategories
    "dog-food": {
        "keywords": ["dry dog food", "wet dog food", "dog biscuits", "pedigree", "optimum dog", "supercoat", "black hawk dog", "advance dog", "royal canin dog"],
        "patterns": [r"(dry|wet)\s+dog\s+food", r"(pedigree|optimum|supercoat|advance|royal canin).*dog"],
    },
    "cat-food": {
        "keywords": ["dry cat food", "wet cat food", "cat biscuits", "whiskas", "dine cat", "fancy feast", "purina cat", "advance cat", "royal canin cat", "meow mix"],
        "patterns": [r"(dry|wet)\s+cat\s+food", r"\bcat\s+(food|treats|biscuits)"],
        "exclude": ["sardine", "fish", "salmon", "tuna", "ocean"],
    },
    "pet-treats": {
        "keywords": ["dog treats", "cat treats", "dog chews", "dental sticks", "schmackos", "pedigree dentastix", "greenies"],
        "patterns": [r"(dog|cat)\s+(treat|chew|stick)", r"(schmackos|dentastix|greenies)"],
    },
}

# Category keywords mapping - slug to list of keywords/patterns
# Based on Woolworths category structure for consistency across stores
CATEGORY_KEYWORDS = {
    "fruit-veg": {
        # Only match clear fresh produce - be very specific
        "keywords": [
            # Fresh veggies that are unique names
            "broccolini", "beetroot", "zucchini", "capsicum", "cucumber",
            "asparagus", "celery", "leek", "fennel", "bok choy", "choy sum",
            # Fresh fruits that are unique names
            "avocado", "rockmelon", "honeydew", "watermelon", "passionfruit",
            "mandarin", "nectarine", "kiwi", "papaya", "dragonfruit",
        ],
        "patterns": [
            # Match actual fresh produce patterns
            r"australian (mango|peach|grape|apple|orange|strawberr|blueberr|raspberr)",
            r"fresh (lettuce|spinach|kale|cabbage|mushroom|tomato|potato|onion)",
            r"bunch each",  # Spring onions, herbs
            r"oakleaf|iceberg|cos lettuce",  # Lettuce varieties
            r"truss.*tomato|cocktail tomato|cherry tomato",  # Tomato varieties
            r"punnet.*g$",  # Punnets of produce
            r"per 200g|per kg|each$",  # Fresh produce sold by weight
            r"woolworths (mushroom|lettuce|onion|potato|tomato|broccoli|carrot)",
            r"coles (kale|lettuce|salad mix|strawberr)",  # Coles branded fresh
            r"^coles (strawberr|banana|apple|orange)",  # Fresh fruit
        ],
        # Exclude everything else
        "exclude": [
            # Electronics
            "airpods", "iphone", "ipad", "macbook", "samsung", "phone", "tablet",
            "earbuds", "headphone", "speaker", "watch", "camera", "generation",
            # Drinks
            "lemonade", "soft drink", "drink", "mineral water", "sparkling", "sports",
            "fanta", "sprite", "solo", "schweppes", "coca", "cola", "pepsi", "gatorade",
            "powerade", "juice", "cordial", "squash", "soda", "fizzy", "energy",
            "smoothie", "milk", "ml", "litre", "bottle", "can", "pack",
            # Snacks
            "popcorn", "corn chips", "tortilla", "chip", "crisps", "pretzels",
            "doritos", "pringles", "thins", "grain waves", "smiths", "cheetos",
            "cracker", "biscuit", "cookie", "shapes", "bar", "pudding", "delights",
            "dip", "dips",
            # Bakery
            "cake", "muffin", "bread", "pastry", "croissant", "tart", "pie", "bagel",
            "wrap", "wraps", "mission",
            # Prepared foods
            "ravioli", "pasta", "risotto", "sausage", "salmon", "beef", "pork",
            "chicken", "lamb", "ham", "bacon", "tuna", "fish", "ricotta",
            "agnolotti", "melters", "fries", "kitchen",
            # Pantry
            "sauce", "paste", "stock", "broth", "seasoning", "dressing", "powder",
            "bolognese", "passata", "baked beans", "spc", "annalisa", "john west",
            # Frozen
            "frozen", "ice cream", "ice block", "gelato", "sorbet", "calippo",
            "streets", "mini",
            # Dairy
            "yoghurt", "yogurt", "cheese", "yoplait", "petit", "pouch",
            # Personal care
            "l'oreal", "loreal", "shampoo", "conditioner", "cream", "lotion",
            # Household
            "dishwashing", "detergent", "cleaning", "fairy", "finish",
            # Baby
            "mamia", "baby", "infant", "toddler",
            # Alcohol
            "wine", "beer", "cider", "vodka", "gin", "rum", "whisky",
            # Deli prepared salads
            "salad co", "salad kit", "coleslaw", "caesar", "asian style",
            "ranch salad", "green goddess", "kaleslaw", "french onion",
        ],
    },
    "meat-seafood": {
        "keywords": [
            # Fresh meat - be more specific
            "chicken breast", "chicken thigh", "beef steak", "lamb chop", "pork chop",
            "beef mince", "lamb mince", "pork mince", "sausage", "bacon rashers",
            "turkey breast", "duck breast", "veal schnitzel", "beef roast", "lamb roast",
            "pork roast", "beef ribs", "pork ribs", "lamb cutlet", "beef fillet",
            "rump steak", "scotch fillet", "eye fillet", "t-bone", "porterhouse",
            # Seafood - be more specific
            "salmon fillet", "tuna steak", "prawns", "king prawns", "barramundi fillet",
            "snapper fillet", "fish fillet", "calamari", "squid", "octopus", "mussels",
            "oyster", "crab", "lobster", "scallop", "marinara mix",
            "frankfurter", "kransky", "chorizo",  # Processed meats
        ],
        "patterns": [r"\bkg\b.*meat", r"per\s*kg", r"fresh\s+seafood"],
        # Exclude products with meat-sounding keywords that aren't meat
        "exclude": [
            # Frozen desserts
            "ice cream", "frozen", "dessert", "gelato", "sorbet",
            "peters drumstick", "paddle pop", "magnum", "cornetto",
            # Snacks with meat flavors - CRITICAL for BBQ issue
            "crackers", "biscuit", "shapes", "cracker", "chips", "cheetos", "balls",
            "twisties", "burger rings", "pringles", "doritos", "thins", "snack",
            "bbq flavour", "bbq flavor", "barbecue flavour", "barbecue flavor",
            "chicken flavour", "chicken flavor", "beef flavour", "beef flavor",
            # Pantry items with meat flavors
            "noodles", "noodle", "stock", "broth", "soup", "sauce", "flavour", "flavor",
            "seasoning", "marinade", "rub", "spice mix",
            # Health supplements
            "fish oil", "oil capsule", "supplement", "vitamin", "capsules", "tablets",
            # Beauty/personal care
            "shampoo", "conditioner", "serum", "moisturiser", "moisturizer", "cream",
            "lotion", "l'oreal", "loreal", "dermaveen", "soap",
            # Bakery - CRITICAL for hot dog rolls issue
            "crumpet", "muffin", "rolls", "buns", "bread", "brioche",
            # Pet food - should go to pet category not meat
            "dog food", "cat food", "pet food", "dog treat", "cat treat",
            "julius", "whiskas", "pedigree", "dine", "fancy feast",
            # Nuts - "roast" matches "roasted" nuts
            "peanut", "macadamia", "almond", "cashew", "walnut", "pistachio",
            "roasted & salted", "roasted and salted", "mixed nuts",
            "forresters",
            # Canned/tinned items
            "canned", "tinned", "can ",
        ],
    },
    "deli": {
        "keywords": [
            "deli", "sliced", "salami", "prosciutto", "pastrami", "mortadella",
            "chorizo", "pepperoni", "kransky", "kabana", "twiggy", "devon",
            "continental", "olives", "antipasto", "hummus", "dip", "tzatziki",
            "guacamole", "pate", "terrine",
            "the fresh salad co",  # ALDI prepared salads
        ],
        "patterns": [
            r"deli\s+", r"sliced\s+(ham|chicken|turkey|roast)",
            r"(potato|coleslaw|pasta|lentil|cous cous) salad",  # Prepared salads
            r"tabbouleh",  # Middle eastern prepared salad
        ],
    },
    "dairy-eggs-fridge": {
        "keywords": [
            "milk", "cheese", "yoghurt", "yogurt", "butter", "cream", "eggs",
            "custard", "sour cream", "cottage cheese", "ricotta", "feta", "fetta", "brie",
            "camembert", "cheddar", "parmesan", "mozzarella", "haloumi", "tasty",
            "cream cheese", "margarine", "spread", "kefir", "quark",
            "havarti", "gouda", "swiss", "emmental", "edam", "colby", "gruyere",
            "emporium selection",  # ALDI cheese brand
        ],
        "patterns": [r"\bL\b.*milk", r"dairy\s+", r"\begg\b", r"slices?\s*\d+g"],
    },
    "bakery": {
        "keywords": [
            "bread", "loaf", "bread rolls", "burger buns", "hot dog rolls", "hot dog buns",
            "croissant", "bagel", "english muffin", "cake", "donut", "doughnut",
            "pastry", "danish pastry", "tart", "scone", "crumpet", "brioche",
            "focaccia", "ciabatta", "sourdough", "rye bread", "wholemeal bread",
            "multigrain bread", "white bread", "wraps", "tortilla", "pita bread",
            "naan bread", "flatbread", "hot cross bun", "fruit loaf", "banana bread",
        ],
        "patterns": [r"bakery\s+", r"sliced\s+bread", r"fresh\s+baked", r"(tip top|abbott|helga|wonder white)"],
        "exclude": ["bread crumbs", "breadcrumbs"],
    },
    "pantry": {
        "keywords": [
            "pasta", "spaghetti", "penne", "fettuccine", "rice", "noodles",
            "cereal", "oats", "muesli", "granola", "sauce", "tomato paste",
            "oil", "olive oil", "vegetable oil", "flour", "sugar", "honey",
            "jam", "peanut butter", "vegemite", "nutella", "spread",
            "canned", "tinned", "beans", "chickpeas", "lentils", "tuna",
            "soup", "stock", "broth", "gravy", "seasoning", "spice", "herbs",
            "salt", "pepper", "vinegar", "soy sauce", "coconut", "curry",
            "mayonnaise", "mayo", "ketchup", "mustard", "relish", "aioli",
            "stonemill", "hillcrest", "oh so natural",  # ALDI brands
        ],
        "patterns": [
            r"cooking\s+", r"baking\s+", r"canned\s+",
            r"diced tomato", r"tomatoes? \d+g",  # Canned tomatoes
            r"chick ?peas?", r"4 bean mix", r"bean mix",  # Canned legumes
            r"ground\s+\d+g", r"leaves\s+\d+g",  # Spices
            r"quinoa|power grain|fruity rings|hooroos",  # Cereals/grains
            r"cup noodle",  # Instant noodles
        ],
    },
    "drinks": {
        "keywords": [
            "water", "juice", "soft drink", "soda", "cola", "lemonade",
            "coffee", "tea", "cordial", "energy drink", "sports drink",
            "mineral water", "sparkling", "coconut water", "kombucha",
            "iced tea", "iced coffee", "flavoured milk", "up & go",
            "powerade", "gatorade", "mother", "v energy", "red bull",
            "westcliff", "quick 2 go", "alcafe", "expressi",  # ALDI brands
        ],
        "patterns": [
            r"\bL\b.*drink", r"sparkling\s+", r"mineral\s+",
            r"(tropical|apple|raspberry) drink",  # Fruit drinks
            r"liquid breakfast",  # Breakfast drinks
            r"drink \d+ pack",  # Multi-pack drinks
            r"capsule|hot choc sachets|latte capsules",  # Coffee pods
        ],
    },
    "freezer": {
        "keywords": [
            "ice cream", "gelato", "sorbet", "frozen pizza", "frozen chips",
            "nuggets", "fish fingers", "ice block", "icy pole", "zooper dooper",
            "frozen pies", "sausage rolls", "party pies", "dim sim", "spring rolls",
            "frozen berries", "frozen vegetables", "frozen peas", "frozen corn",
            "frozen meals", "ready meals", "frozen dessert", "waffles",
            "orchard & vine", "seasons pride", "earth grown",  # ALDI frozen brands
        ],
        "patterns": [
            r"frozen\s+", r"ice\s+cream",
            r"(mixed )?berries \d+g",  # Frozen berries (ALDI)
            r"blueberries \d+g",  # Frozen blueberries
            r"samosa|spring roll|dim sim",  # Frozen snacks
            r"gratin \d+g",  # Frozen potato dishes
            r"french fries|steakhouse fries|chips \d+kg",  # Frozen fries
            r"veggie burger|plant.based",  # Meat alternatives
        ],
        # Exclude non-frozen products that contain "frozen" in name
        "exclude": [
            # Disney Frozen themed products
            "toothbrush", "oral b", "oral-b", "spiderman", "disney",
            # Snack crackers with pizza/chips flavors
            "shapes", "arnott", "crackers", "cracker", "vege chips",
            # Other non-frozen items
            "frozen shoulder", "frozen moment",
        ],
    },
    "snacks-confectionery": {
        "keywords": [
            "chocolate", "chips", "crisps", "lollies", "candy", "biscuit",
            "cookie", "cracker", "popcorn", "pretzels", "rice crackers",
            "muesli bar", "protein bar", "snack bar", "tim tam", "shapes",
            "twisties", "doritos", "pringles", "oreo", "m&m", "snickers",
            "mars", "twix", "kit kat", "cadbury", "nestle", "lindt",
            "gummy", "jelly", "licorice", "mints", "chewing gum", "5gum",
            "cheetos", "puffs", "burger rings", "cheezels", "in a biskit",
            "thins", "cc's", "grain waves", "kettle", "samboy", "arnott",
            "ferrero", "raffaello", "rocher", "kinder", "maltesers", "favourites",
            "forresters", "dominion naturals", "sweet vine",  # ALDI brands
        ],
        "patterns": [
            r"cadbury\s+", r"nestle\s+", r"smith", r"red rock", r"snack", r"gift\s+box",
            r"natural (almonds?|cashews?|macadamia|walnut|pistachio)",  # Nuts
            r"(almonds?|cashews?|macadamias?) \d+g",  # Nut packs
            r"dried (fig|apricot|mango|apple|cranberr|garland)",  # Dried fruit
            r"(cowboy|superfood|trail) mix",  # Nut mixes
            r"snakes|party mix|lollies",  # Confectionery
            r"oat bar|protein.*pudding",  # Snack bars
            # BBQ-flavored snacks - CRITICAL to capture these here
            r"bbq\s+(shapes|chips|flavour|flavor)", r"barbecue\s+(shapes|chips|flavour)",
            r"(arnott|shapes).*bbq",  # Arnott's BBQ products
        ],
        "exclude": ["roasted nuts", "salted nuts", "mixed nuts"],  # Nuts go to nuts-snacks subcategory
    },
    "international": {
        "keywords": [
            "asian", "mexican", "italian", "indian", "thai", "chinese",
            "japanese", "korean", "vietnamese", "middle eastern", "greek",
            "taco", "burrito", "enchilada", "salsa", "curry paste", "satay",
            "teriyaki", "miso", "tofu", "tempeh", "wonton", "dumpling",
            "ramen", "udon", "soba", "rice paper", "fish sauce", "sriracha",
            "nongshim", "shin ramyun", "stir fry", "kimchi", "gochujang",
        ],
        "patterns": [r"asian\s+", r"mexican\s+", r"indian\s+", r"stir\s+fry"],
    },
    "liquor": {
        "keywords": [
            # Multi-word keywords safe from substring matches
            "craft beer", "pale ale", "dry gin", "spiced rum", "white rum", "dark rum",
            "vodka", "whisky", "whiskey", "tequila", "bourbon", "scotch", "brandy",
            "liqueur", "champagne", "prosecco", "sparkling wine", "apple cider",
            "lager", "stout", "port wine", "sherry", "vermouth", "aperol", "campari",
            "cabernet", "shiraz", "chardonnay", "merlot", "pinot", "sauvignon",
            "tempranillo", "rioja", "riesling", "moscato", "sangria",
            "jack daniel", "johnnie walker", "jim beam", "corona", "heineken",
            "carlton", "victoria bitter", "coopers", "xxxx gold",
            "-196",  # Japanese RTD brand
        ],
        "patterns": [
            r"\bbeer\b", r"\bwine\b", r"\bgin\b", r"\bale\b", r"\brum\b",  # Word boundaries for short words
            r"\bcider\b", r"\bspirits?\b",
            r"\d+\s*ml.*alcohol", r"750\s*m(l|illilitre)",
            r"docg|vintage \d{4}",  # Wine designations
        ],
        "exclude": ["ginger", "original", "vingegar", "vinegar", "cinnamon", "cumberland", "goldenvale", "oats", "porridge", "rice", "chips", "crackers", "biscuit", "maple", "whiting", "fish", "fillet"],
    },
    "beauty": {
        "keywords": [
            "makeup", "cosmetics", "foundation", "mascara", "lipstick",
            "eyeliner", "eyeshadow", "blush", "concealer", "primer",
            "nail polish", "perfume", "fragrance", "cologne", "moisturiser",
            "serum", "face mask", "cleanser", "toner", "sunscreen",
            "l'oreal", "loreal", "revitalift", "maybelline", "rimmel",
            "olay", "nivea face", "neutrogena", "garnier", "dove",
            "anti-wrinkle", "anti wrinkle", "skin care", "skincare",
        ],
        "patterns": [r"beauty\s+", r"cosmetic", r"face\s+(cream|wash|scrub)"],
    },
    "personal-care": {
        "keywords": [
            "shampoo", "conditioner", "soap", "body wash", "deodorant",
            "toothpaste", "toothbrush", "mouthwash", "razor", "shaving",
            "hair dye", "hair colour", "styling", "gel", "mousse", "hairspray",
            "lotion", "body lotion", "hand cream", "lip balm", "cotton",
            "feminine", "tampon", "pad", "sanitary",
            "prince", "nivea men",  # Shaving brands
        ],
        "patterns": [
            r"shampoo\s+", r"body\s+wash", r"tooth",
            r"shave foam|blade.*cartridge|replacement cartridge",  # Shaving
        ],
    },
    "health": {
        "keywords": [
            "vitamin", "supplement", "panadol", "nurofen", "aspirin",
            "cold", "flu", "allergy", "hayfever", "bandage", "band-aid",
            "first aid", "pain relief", "antacid", "probiotic", "fish oil",
            "multivitamin", "protein powder", "collagen",
            "nature's way", "swisse", "blackmores", "cenovis", "ostelin",
            "vitagummie", "omega", "glucosamine", "magnesium", "zinc",
            "melatonin", "echinacea", "turmeric", "elderberry",
            "essential health",  # ALDI health brand
        ],
        "patterns": [
            r"vitamin\s+", r"supplement", r"pain\s+relief", r"\d+mg\s+tablet",
            r"electrolyte",  # Sports/health drinks
        ],
    },
    "cleaning-household": {
        "keywords": [
            "detergent", "laundry", "washing", "cleaning", "wipes", "bleach",
            "disinfectant", "air freshener", "surface spray", "bathroom",
            "kitchen", "floor", "glass cleaner", "stain remover", "fabric",
            "paper towel", "toilet paper", "tissues", "bin bags", "garbage",
            "dishwashing", "dish soap", "rinse aid", "dishwasher tablets",
            "sponge", "cloth", "mop", "broom", "gloves",
            "biozet", "omo", "cold power", "dynamo", "napisan", "vanish",
            "finish", "fairy", "morning fresh", "palmolive", "ajax",
            "dettol", "glen 20", "pine o cleen", "exit mould",
            "battery", "batteries", "duracell", "energizer", "light bulb",
            "blu tack", "adhesive", "tape", "marker", "pen", "stationery",
            "power force",  # ALDI cleaning brand
        ],
        "patterns": [
            r"cleaning\s+", r"spray\s+", r"wipes", r"liquid\s+\d",
            r"mould away|oven cleaner|sandwich bag",  # Cleaning products
        ],
    },
    "baby": {
        "keywords": [
            "nappy", "nappies", "diaper", "formula", "baby food", "baby wipes",
            "baby wash", "baby shampoo", "baby lotion", "baby powder",
            "sippy cup", "bottle", "dummy", "pacifier", "teething",
            "huggies", "pampers", "aptamil", "s26", "karicare",
            "mamia",  # ALDI baby brand
        ],
        "patterns": [r"baby\s+", r"infant", r"toddler", r"12\+ months"],
    },
    "pet": {
        "keywords": [
            "dog food", "cat food", "pet food", "kitty litter", "cat litter",
            "dog treats", "cat treats", "pet treats", "flea", "tick",
            "worming", "pet shampoo", "bird seed", "fish food",
            "whiskas", "pedigree", "dine", "fancy feast", "royal canin",
            "advance", "black hawk", "optimum",
        ],
        "patterns": [r"pet\s+food", r"dog\s+food", r"dog\s+treat", r"cat\s+food", r"cat\s+treat"],
        # Exclude non-pet products
        "exclude": [
            "chewing gum", "5gum", "gum tropical", "gum peppermint", "gum spearmint",
        ],
    },
}


def extract_primary_product(name: str) -> str:
    """
    Extract the primary product from a product name by stripping descriptors.

    Examples:
        "John West Tuna In Tomato And Onion Savoury Sauce 95g" -> "john west tuna"
        "Heinz Tomato Sauce 500ml" -> "heinz tomato sauce"
        "Chicken With Vegetables 400g" -> "chicken"

    Args:
        name: Full product name

    Returns:
        Cleaned product name with descriptors removed
    """
    text = name.lower()

    # Strip descriptor patterns
    for pattern in DESCRIPTOR_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return text.strip()


def _calculate_match_score(text: str, rules: dict, category_slug: str) -> int:
    """
    Calculate a match score for a category based on keywords and patterns.

    Returns:
        Score (0 if no match, higher = better match)
    """
    # Check exclusions first - if any exclusion matches, return 0
    exclusions = rules.get("exclude", [])
    if any(excl in text for excl in exclusions):
        return 0

    score = 0

    # Keywords get higher base score than patterns
    for keyword in rules.get("keywords", []):
        if keyword in text:
            # Longer keyword matches are more specific
            score = max(score, 100 + len(keyword))

    # Patterns get moderate score
    for pattern in rules.get("patterns", []):
        if re.search(pattern, text, re.IGNORECASE):
            score = max(score, 50)

    # Apply category priority modifier
    priority = CATEGORY_PRIORITY.get(category_slug, 50)
    if score > 0:
        score += priority

    return score


def categorize_product(name: str, brand: Optional[str] = None) -> Optional[str]:
    """
    Auto-categorize a product based on its name and brand.
    Uses priority-based scoring to handle ambiguous matches.

    Features:
    - Strips descriptor patterns to identify primary product
    - Uses scoring system instead of first-match-wins
    - Higher priority categories win when multiple matches exist

    Args:
        name: Product name (e.g., "John West Tuna In Tomato Sauce 95g")
        brand: Optional brand name (e.g., "John West")

    Returns:
        Category slug (e.g., "canned-food") or None if no match

    Examples:
        "John West Tuna In Tomato Sauce 95g" -> "canned-food" (not "sauces-condiments")
        "Heinz Tomato Sauce 500ml" -> "sauces-condiments"
        "Arnott's Shapes BBQ 175g" -> "biscuits" (not "sausages-bbq")
    """
    if not name:
        return None

    # Combine name and brand for matching
    text = f"{name} {brand or ''}".lower()

    # Also try matching with primary product only (descriptors stripped)
    primary_text = extract_primary_product(f"{name} {brand or ''}")

    matches: List[Tuple[str, int]] = []  # List of (category_slug, score)

    # Check all subcategories and collect matches with scores
    for subcategory_slug, rules in SUBCATEGORY_KEYWORDS.items():
        # Try matching full text first
        score = _calculate_match_score(text, rules, subcategory_slug)

        # If no match on full text, try primary product text
        if score == 0:
            score = _calculate_match_score(primary_text, rules, subcategory_slug)

        if score > 0:
            matches.append((subcategory_slug, score))

    # If we have subcategory matches, return the best one
    if matches:
        best_match = max(matches, key=lambda x: x[1])
        return best_match[0]

    # Fall back to parent categories
    matches = []
    for category_slug, rules in CATEGORY_KEYWORDS.items():
        score = _calculate_match_score(text, rules, category_slug)

        if score == 0:
            score = _calculate_match_score(primary_text, rules, category_slug)

        if score > 0:
            matches.append((category_slug, score))

    if matches:
        best_match = max(matches, key=lambda x: x[1])
        return best_match[0]

    return None


def categorize_batch(products: list[dict]) -> dict[int, str]:
    """
    Categorize multiple products at once.

    Args:
        products: List of dicts with 'id', 'name', and optional 'brand'

    Returns:
        Dict mapping product_id to category_slug
    """
    results = {}
    for product in products:
        category = categorize_product(
            product.get("name", ""),
            product.get("brand")
        )
        if category:
            results[product["id"]] = category
    return results


def get_category_suggestions(name: str, brand: Optional[str] = None) -> list[str]:
    """
    Get all possible category matches for a product (for manual review).

    Returns list of category slugs ordered by confidence.
    """
    if not name:
        return []

    text = f"{name} {brand or ''}".lower()
    matches = []

    for category_slug, rules in CATEGORY_KEYWORDS.items():
        score = 0
        # Count keyword matches
        for keyword in rules["keywords"]:
            if keyword in text:
                score += 1
        # Count pattern matches
        for pattern in rules.get("patterns", []):
            if re.search(pattern, text, re.IGNORECASE):
                score += 1

        if score > 0:
            matches.append((category_slug, score))

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matches]
