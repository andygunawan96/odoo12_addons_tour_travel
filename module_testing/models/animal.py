from odoo import api,models,fields


ANIMAL_TYPE = [
    ('flying', 'Flying Animal'),
    ('walking', 'Walking Animal'),
    ('swimming', 'Swimming Animal')
]

STATE_STR_TO_INDEX = {
    'flying' : 0,
    'walking' : 1,
    'swimming' : 2,
}

class FlyingAnimal(models.Model):
    _name = 'testing.flying.animal'
    # _inherits = {'testing.animal' : 'base_animal_id'}

    wing_swing = fields.Integer('Wing Swings', readonly=True)
    wing_swing2 = fields.Integer('Wing Swings', readonly=True)
    # base_animal_id = fields.Many2one('testing.animal')
    # def fly(self):

    def move_forward(self):
        self.wing_swing += 6

    def report(self):
        return [
            'wing_swing',
            'wing_swing2'
        ]

class WalkingAnimal(models.Model):
    _name = 'testing.walking.animal'
    # _inherits = {'testing.animal' : 'base_animal_id'}

    steps = fields.Integer('Steps', readonly=True)
    same_field = fields.Integer('Walking Same', readonly=True)
    # base_animal_id = fields.Many2one('testing.animal')

    def move_forward(self):
        self.steps += 1
        self.same_field += 3

    def report(self):
        return [
            'steps',
            'steps2'
        ]

class SwimmingAnimal(models.Model):
    _name = 'testing.swimming.animal'
    # _inherits = {'testing.animal' : 'base_animal_id'}

    thrust = fields.Integer('Thrust', readonly=True)
    same_field = fields.Integer('Swimming Same', readonly=True)
    # base_animal_id = fields.Many2one('testing.animal')

    def move_forward(self):
        self.thrust += 2
        self.same_field += 7

    def report(self):
        return [
            'thrust',
            'thrust2'
        ]

class Animal(models.Model):
    _name = 'testing.animal'
    _inherits = {
        'testing.flying.animal': 'flying_animal_id',
        'testing.walking.animal': 'walking_animal_id',
        'testing.swimming.animal': 'swimming_animal_id',
    }

    name = fields.Char('Name')
    habitat = fields.Char('Habitat')
    owner_id = fields.Many2one('orang.orang', 'Owner')
    state = fields.Selection(ANIMAL_TYPE, 'Animal Type')



    flying_animal_id = fields.Many2one('testing.flying.animal')
    walking_animal_id = fields.Many2one('testing.walking.animal')
    swimming_animal_id = fields.Many2one('testing.swimming.animal')

    # def __init__(self, _cr, _pool):
    #     super(Animal, self).__init__(_cr, _pool)
    #     self.animal_types = [
    #         self.flying_animal_id,
    #         self.walking_animal_id,
    #         self.swimming_animal_id
    #     ]

    def provide_animal_types(self):
        return {
            'flying' : self.flying_animal_id,
            'walking' : self.walking_animal_id,
            'swimming' : self.swimming_animal_id
        }

    def move_forward_animal(self):
        # self.swimming_animal_id.move_forward()
        animal_types = self.provide_animal_types()
        animal_types[self.state].move_forward()

    def report_animal(self):
        animal_types = self.provide_animal_types()

        keys = [
            'name','habitat','owner_id','state'
        ]

        extra_keys = animal_types[self.state].report()
        for key in extra_keys:
            keys.append(key)

        rec = self.sudo().search([('create_date','>',self.create_date),('state','=',self.state)])
        for rec2 in rec:
            result_dict = {}
            for key in keys:
                result_dict[key] = rec2[key]
            print(result_dict)

    def test_search(self):
        rec = self.sudo().search([('thrust','=','94')])
        print(rec.thrust)




