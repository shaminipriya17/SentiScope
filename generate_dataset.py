import pandas as pd

positive_reviews = [
    "Excellent product and amazing quality",
    "I love this item",
    "Very satisfied with the purchase",
    "Great battery life",
    "Fantastic camera quality"
] * 20

negative_reviews = [
    "Very poor quality",
    "Completely disappointed",
    "Battery drains quickly",
    "Not worth the money",
    "Worst product ever"
] * 20

neutral_reviews = [
    "The product is okay",
    "Average performance",
    "Nothing special",
    "Works as expected",
    "Decent product"
] * 20

reviews = []
sentiments = []

for review in positive_reviews:
    reviews.append(review)
    sentiments.append("Positive")

for review in negative_reviews:
    reviews.append(review)
    sentiments.append("Negative")

for review in neutral_reviews:
    reviews.append(review)
    sentiments.append("Neutral")

df = pd.DataFrame({
    "review": reviews,
    "sentiment": sentiments
})

df.to_csv("dataset/reviews.csv", index=False)

print("Dataset created successfully!")
print("Location: dataset/reviews.csv")