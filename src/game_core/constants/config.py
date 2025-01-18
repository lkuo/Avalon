from game_core.constants.role import Role

DEFAULT_QUEST_TEAM_SIZE = {
    5: {1: 2, 2: 3, 3: 2, 4: 3, 5: 3},
    6: {1: 2, 2: 3, 3: 4, 4: 3, 5: 4},
    7: {1: 2, 2: 3, 3: 3, 4: 4, 5: 4},
    8: {1: 3, 2: 4, 3: 4, 4: 5, 5: 5},
    9: {1: 3, 2: 4, 3: 4, 4: 5, 5: 5},
    10: {1: 3, 2: 4, 3: 4, 4: 5, 5: 5},
}
KNOWN_ROLES = {
    Role.Merlin.value: [Role.Morgana.value, Role.Assassin.value, Role.Oberon.value],
    Role.Percival.value: [Role.Merlin.value, Role.Morgana.value],
    Role.Mordred.value: [
        Role.Morgana.value,
        Role.Assassin.value,
        Role.Oberon.value,
    ],
    Role.Morgana.value: [
        Role.Mordred.value,
        Role.Assassin.value,
        Role.Oberon.value,
    ],
    Role.Assassin.value: [
        Role.Mordred.value,
        Role.Morgana.value,
        Role.Oberon.value,
    ],
    Role.Oberon.value: [],
    Role.Villager.value: [],
}
DEFAULT_ASSASSINATION_ATTEMPTS = 1
