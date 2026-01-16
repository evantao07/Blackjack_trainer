import random

ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
suits = ["♠","♥","♦","♣"]

def make_deck():
    deck = []
    for s in suits:
        for r in ranks:
            deck.append(r + s)
    random.shuffle(deck)
    return deck

def card_rank(card):
    # card looks like "10♠" or "A♥"
    return card[:-1]  # suit is last char

def hand_value(hand):
    # count A as 11 first, then fix if bust
    total = 0
    aces = 0

    for card in hand:
        r = card_rank(card)
        if r in ["J","Q","K"]:
            total += 10
        elif r == "A":
            total += 11
            aces += 1
        else:
            total += int(r)

    # turn some aces into 1 if needed
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total

def show_hand(name, hand, hide_first=False):
    if hide_first:
        print(name + ": " + hand[0] + " ??")
    else:
        print(name + ": " + " ".join(hand) + "  (total: " + str(hand_value(hand)) + ")")

def main():
    print("Evan's Game of BlackJacks")
    print("Type 'n' at the end of a round to quit.\n")

    deck = make_deck()
    wins = 0
    losses = 0
    ties = 0

    while True:
        # reshuffle if deck is low
        if len(deck) < 15:
            deck = make_deck()

        # deal
        player = []
        dealer = []
        player.append(deck.pop())
        dealer.append(deck.pop())
        player.append(deck.pop())
        dealer.append(deck.pop())

        print("\n----------------------------")
        show_hand("Dealer", dealer, hide_first=True)
        show_hand("Player", player)

        # check blackjack right away
        player_bj = (hand_value(player) == 21 and len(player) == 2)
        dealer_bj = (hand_value(dealer) == 21 and len(dealer) == 2)

        if player_bj or dealer_bj:
            print("\nDealer reveals:")
            show_hand("Dealer", dealer, hide_first=False)

            if player_bj and dealer_bj:
                print("Push. (Both blackjack)")
                ties += 1
            elif player_bj:
                print("Blackjack! You win.")
                wins += 1
            else:
                print("Dealer has blackjack. You lose.")
                losses += 1

        else:
            # player turn
            while True:
                if hand_value(player) > 21:
                    print("\nYou busted!")
                    break

                move = input("Hit or Stand? (h/s): ").lower().strip()
                if move == "h":
                    player.append(deck.pop())
                    print()
                    show_hand("Dealer", dealer, hide_first=True)
                    show_hand("Player", player)
                elif move == "s":
                    break
                else:
                    print("Type h or s.")

            # if player bust, round over
            if hand_value(player) > 21:
                print("You lose.")
                losses += 1
                print("\nDealer reveals:")
                show_hand("Dealer", dealer, hide_first=False)
            else:
                # dealer turn
                print("\nDealer reveals:")
                show_hand("Dealer", dealer, hide_first=False)

                while hand_value(dealer) < 17:
                    print("Dealer hits...")
                    dealer.append(deck.pop())
                    show_hand("Dealer", dealer, hide_first=False)

                # decide winner
                p = hand_value(player)
                d = hand_value(dealer)

                if d > 21:
                    print("Dealer busted! You win.")
                    wins += 1
                else:
                    if p > d:
                        print("You win.")
                        wins += 1
                    elif p < d:
                        print("You lose.")
                        losses += 1
                    else:
                        print("Push. (tie)")
                        ties += 1

        # scoreboard
        print("\nScoreboard -> Wins:", wins, "Losses:", losses, "Ties:", ties)

        again = input("Play again? (enter: 'n/no' to quit): ").lower().strip()
        if again == "n" or again == "no":
            break

    print("\nThanks for playing!")

if __name__ == "__main__":
    main()
