"""
curriculum.py — Task difficulty scheduler for training.


Implements a 3-stage curriculum:


Episodes 0–20:
   → Task 1 only


Episodes 20–50:
   → Task 1 (30%), Task 2 (70%)


Episodes 50+:
   → Task 1 (20%), Task 2 (40%), Task 3 (40%)


This returns a task_id (1, 2, or 3) for each episode.
"""


import random




def get_task_id(episode: int) -> int:
   """
   Return a task_id based on the episode number.
   """


   if episode < 20:
       return 1


   elif episode < 50:
       return random.choices(
           population=[1, 2],
           weights=[0.3, 0.7],
           k=1
       )[0]


   else:
       return random.choices(
           population=[1, 2, 3],
           weights=[0.2, 0.4, 0.4],
           k=1
       )[0]




def get_curriculum_distribution(episode: int) -> dict:
   """
   Returns the probability distribution for logging/debugging.
   """
   if episode < 20:
       return {1: 1.0, 2: 0.0, 3: 0.0}


   elif episode < 50:
       return {1: 0.3, 2: 0.7, 3: 0.0}


   else:
       return {1: 0.2, 2: 0.4, 3: 0.4}
