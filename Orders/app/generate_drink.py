import random
from pydantic import BaseModel
from Orders.config.options import *
from typing import Optional, Set

class Drink(BaseModel):
    drink: str
    milk: str
    shots: int
    texture: Optional[str]
    temperature: str
    options: Set[str]

    @staticmethod
    def generateDrink():
        '''
        Random drink generator.
        Generates an espresso based drink of certain type, with randomly chosen milk type, 
        shot number, milk texture and temperature, and other options.
        '''
        #Choose drink and milk type
        drink_choice = random.choice(list(DRINKS.keys()))
        milk_choice = random.choice(MILKS)

        #Choose options
        options = set()
        n = random.randint(0, 2)
        while n > 0:
            option = random.choice(OPTIONS)
            options.add(option)
            n -= 1
        
        #Choose how many additional shots of espresso
        if random.randint(0, 100) < 30:
            shot_choice = random.choice(list(SHOT_OPTIONS.keys()))
        else:
            shot_choice = None
        #Calculate number of shots
        default_shots = DRINKS[drink_choice]['shots']
        if shot_choice == 'single_shot':
            shots = 1
        if shot_choice == 'extra_shot':
            shots = default_shots + 1
        if shot_choice == 'extra_shot_x2':
            shots = default_shots + 2
        else:
            shots = default_shots

        #Choose milk texture
        if random.randint(0, 100) < 10:
            texture = random.choice(TEXTURES[0:2])
        else:
            texture = DRINKS[drink_choice]['texture']

        #Choose milk temperature
        if random.randint(0, 100) < 25:
            temperature = random.choice(TEMPERATURES)
        else:
            temperature = 'normal'
        
        #Compile and return drink information
        drink = Drink(
            drink = drink_choice,
            milk = milk_choice,
            options = options,
            shots = shots,
            texture = texture,
            temperature = temperature
        )

        return drink
