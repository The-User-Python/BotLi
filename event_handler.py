import queue
from queue import Queue
from threading import Thread

from api import API
from challenge_validator import Challenge_Validator
from game_manager import Game_Manager


class Event_Handler(Thread):
    def __init__(self, config: dict, api: API, game_manager: Game_Manager) -> None:
        Thread.__init__(self)
        self.config = config
        self.api = api
        self.is_running = True
        self.game_manager = game_manager
        self.challenge_validator = Challenge_Validator(config)

    def start(self):
        Thread.start(self)

    def stop(self):
        self.is_running = False

    def run(self) -> None:
        challenge_queue = Queue()
        challenge_queue_thread = Thread(target=self.api.get_event_stream, args=(challenge_queue,), daemon=True)
        challenge_queue_thread.start()

        while self.is_running:
            try:
                event = challenge_queue.get(timeout=2)
            except queue.Empty:
                continue

            if event['type'] == 'challenge':
                print(event)
                challenger_name = event['challenge']['challenger']['name']

                if challenger_name == self.api.user['username']:
                    continue

                print(self.challenge_validator.format_challenge_event(event))

                challenge_id = event['challenge']['id']
                if decline_reason := self.challenge_validator.get_decline_reason(event):
                    self.api.decline_challenge(challenge_id, decline_reason)
                    continue

                self.game_manager.add_challenge(challenge_id)
                print(f'Challenge "{challenge_id}" added to queue.')
            elif event['type'] == 'gameStart':
                game_id = event['game']['id']

                self.game_manager.on_game_started(game_id)
            elif event['type'] == 'gameFinish':
                game_id = event['game']['id']

                self.game_manager.on_game_finished(game_id)
            elif event['type'] == 'challengeDeclined':
                opponent_name = event['challenge']['destUser']['name']

                if opponent_name == self.api.user['username']:
                    continue

                decline_reason = event['challenge']['declineReason']
                print(f'{opponent_name} declined challenge: {decline_reason}')
            elif event['type'] == 'challengeCanceled':
                challenge_id = event['challenge']['id']
                self.game_manager.remove_challenge(challenge_id)
            else:
                print(event)
