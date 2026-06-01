import random

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]

SEASON_MULTIPLIERS = {
    "Spring": {"Wheat": 0.77, "Timber": 1.0, "Sheep": 0.77, "Stone": 1.25, "Clay": 1.67},
    "Summer": {"Wheat": 0.67, "Timber": 0.83, "Sheep": 1.25, "Stone": 1.0, "Clay": 0.77},
    "Autumn": {"Wheat": 1.25, "Timber": 0.67, "Sheep": 0.83, "Stone": 1.0, "Clay": 1.0},
    "Winter": {"Wheat": 2.5, "Timber": 1.67, "Sheep": 1.67, "Stone": 0.71, "Clay": 1.43},
}

EVENTS = {
    "Drought":           {"Wheat": 3.33},
    "Plague":            {"Sheep": 2.5},
    "Construction Boom":  {"Stone": 1.8, "Timber": 1.5},
    "Flood":             {"Clay": 3.33, "Wheat": 2.0},
    "Mild Season":       {"Wheat": 1.11, "Timber": 1.11, "Sheep": 1.11, "Stone": 1.11, "Clay": 1.11},
    "Wildfire":          {"Timber": 2.5},
    "Earthquake":        {"Stone": 2.5, "Clay": 2.0},
    "Gold Rush":         {"Wheat": 1.3, "Timber": 1.3, "Sheep": 1.3, "Stone": 1.3, "Clay": 1.3},
    "Plentiful Harvest":  {"Wheat": 0.6, "Sheep": 0.6},
}

MAX_HISTORY = 300


class Resource:
    def __init__(self, name, base_price):
        self.name = name
        self.base_price = base_price
        self.pool = 50
        self.baseline = 50
        self.event_multiplier = 1.0
        self.event_active = False
        self.price_history = []
        self._season_factor = 1.0
        self._event_factor = 1.0

    def get_season_multiplier(self, season):
        return SEASON_MULTIPLIERS[season].get(self.name, 1.0)

    def calculate_price(self, season):
        effective_pool = max(1, self.pool)
        return max(1, self.base_price * (self.baseline / effective_pool) * self._season_factor * self._event_factor)

    def _record_price(self, season):
        self.price_history.append(self.calculate_price(season))
        if len(self.price_history) > MAX_HISTORY:
            self.price_history.pop(0)

    def buy(self, amount, season):
        self.pool = max(0, self.pool - amount)
        self._record_price(season)

    def sell(self, amount, season):
        self.pool += amount
        self._record_price(season)

    def seasonal_reset(self):
        self.pool += (self.baseline - self.pool) * 0.3

    def tick_update(self, season):
        target_s = SEASON_MULTIPLIERS[season].get(self.name, 1.0)
        self._season_factor += (target_s - self._season_factor) * 0.4
        target_e = self.event_multiplier if self.event_active else 1.0
        self._event_factor += (target_e - self._event_factor) * 0.4


class Market:
    def __init__(self):
        self.season_index = 0
        self.event_name = None
        self.resources = [
            Resource("Wheat", 10),
            Resource("Timber", 10),
            Resource("Sheep", 10),
            Resource("Stone", 10),
            Resource("Clay", 10),
        ]
        for r in self.resources:
            r._season_factor = r.get_season_multiplier(self.season)
            r._record_price(self.season)

    @property
    def season(self):
        return SEASONS[self.season_index]

    def advance_season(self):
        self.season_index = (self.season_index + 1) % 4
        for r in self.resources:
            r.seasonal_reset()

    def _clear_event(self):
        self.event_name = None
        for r in self.resources:
            r.event_multiplier = 1.0
            r.event_active = False

    def toggle_event(self, event_name=None):
        if self.event_name is not None:
            self._clear_event()
        elif event_name is not None:
            self.event_name = event_name
            multipliers = EVENTS[event_name]
            for r in self.resources:
                if r.name in multipliers:
                    r.event_multiplier = multipliers[r.name]
                    r.event_active = True
                else:
                    r.event_multiplier = 1.0
                    r.event_active = False
        else:
            self.event_name = random.choice(list(EVENTS.keys()))
            multipliers = EVENTS[self.event_name]
            for r in self.resources:
                if r.name in multipliers:
                    r.event_multiplier = multipliers[r.name]
                    r.event_active = True
                else:
                    r.event_multiplier = 1.0
                    r.event_active = False

    def tick(self):
        for r in self.resources:
            r.pool += (r.baseline - r.pool) * 0.04 + random.uniform(-0.5, 0.5)
            if random.random() < 0.2:
                r.pool += random.gauss(0, 3)
            r.tick_update(self.season)
            r._record_price(self.season)

    def get_resource(self, name):
        for r in self.resources:
            if r.name.lower() == name.lower():
                return r
        return None

    def set_pool_size(self, new_size):
        for r in self.resources:
            r.pool = new_size
            r.baseline = new_size

    def set_base_price(self, price):
        for r in self.resources:
            r.base_price = price

    def buy(self, resource_name, amount):
        r = self.get_resource(resource_name)
        if r:
            r.buy(amount, self.season)

    def sell(self, resource_name, amount):
        r = self.get_resource(resource_name)
        if r:
            r.sell(amount, self.season)
