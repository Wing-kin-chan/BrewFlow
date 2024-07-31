DRINKS = {
    'latte': {'shots': 2, 'texture': 'wet'},
    'small_latte': {'shots': 1, 'texture': 'wet'},
    'cappuccino': {'shots': 2, 'texture': 'dry'},
    'small_cappuccino': {'shots': 1, 'texture': 'dry'},
    'long_black': {'shots': 2, 'texture': None},
    'short_black': {'shots': 2, 'texture': None},
    'flat_white':{'shots': 2, 'texture': 'wet'},
    'double_espresso': {'shots': 2, 'texture': None},
    'single_espresso': {'shots': 1, 'texture': None},
    'macchiato': {'shots': 2, 'texture': 'dry'},
    'single_macchiato': {'shots': 1, 'texture': 'dry'},
    'cortado': {'shots': 2, 'texture': 'wet'}
}
TEXTURES = ['wet', 'dry', None]
TEMPERATURES = ['normal', 'extra_hot', 'warm']
MILKS = ['full_fat', 'semi_skimmed', 'oat', 'soy']
OPTIONS = ['agave', 'honey', 'decaf', 'chocolate', 'cinnamon']
SHOT_OPTIONS = {'extra_shot': 1,
                'extra_shot_x2': 2,
                'single_shot': 1}