from datetime import date, timedelta
from database import Poll, PollAnswer, User

def get_closest_weekday(target_weekday: int) -> date:
    """Returns the closest upcoming date for the given weekday (0=Mon, 6=Sun)."""
    today = date.today()
    days_until = (target_weekday - today.weekday()) % 7
    if days_until == 0:
        days_until = 7
    return today + timedelta(days=days_until)

def calculate_day_winner(poll_id: int, db) -> tuple[str, list[User], list[User]]:
    """
    Calculates the winning day from a choose_day poll.
    Returns:
        winning_day_text (str): The text of the winning option.
        losers (list[User]): Users who voted ONLY for the losing day(s).
        tied_users (list[User]): If there's a tie, users who voted for the tied days.
    """
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll or not poll.options:
        return "Неизвестный день", [], []

    options = poll.options.split(",")
    answers = db.query(PollAnswer).filter(PollAnswer.poll_id == poll_id).all()

    if not answers:
        return "Неизвестный день", [], []

    # Count votes
    vote_counts = {str(i): 0 for i in range(len(options))}
    user_votes = {} # user_id -> set of option indices

    for answer in answers:
        chosen_indices = answer.option_ids.split(",")
        user_votes[answer.user_id] = set(chosen_indices)
        for idx in chosen_indices:
            if idx in vote_counts:
                vote_counts[idx] += 1

    # Exclude "Не приду" (usually the last option) from winning consideration if possible
    # Assuming "Не приду" is the last option
    not_coming_idx = str(len(options) - 1)
    
    # Find max votes among actual days
    valid_votes = {k: v for k, v in vote_counts.items() if k != not_coming_idx}
    if not valid_votes or all(v == 0 for v in valid_votes.values()):
        return "Голосов нет", [], []

    max_votes = max(valid_votes.values())
    winning_indices = [k for k, v in valid_votes.items() if v == max_votes]

    if len(winning_indices) == 1:
        winner_idx = winning_indices[0]
        winning_day_text = options[int(winner_idx)].split(" (")[0] # Strip the date part for brevity, e.g., "Суббота"
        
        # Find losers: users who voted for valid days, but NOT the winning day
        losers = []
        for user_id, voted_indices in user_votes.items():
            if not_coming_idx in voted_indices and len(voted_indices) == 1:
                continue # They aren't coming anyway
            if winner_idx not in voted_indices:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    losers.append(user)
                    
        return winning_day_text, losers, []

    else:
        # Tie!
        winning_day_text = "/".join([options[int(idx)].split(" (")[0] for idx in winning_indices])
        tied_users = []
        for user_id, voted_indices in user_votes.items():
            # If they voted for ANY of the tied days, they are involved in the tie
            if any(idx in voted_indices for idx in winning_indices):
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    tied_users.append(user)
                    
        return winning_day_text, [], tied_users
