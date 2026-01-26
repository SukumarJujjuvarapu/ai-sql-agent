import sqlite3
import pandas as pd

# 1. Connect to the database
# The file name must match exactly what is in your folder
db_path = 'Chinook_Sqlite.sqlite'
conn = sqlite3.connect(db_path)

print("Connection Established!")

# 2. Our first "System Query"
# This SQL query asks the database to list all its tables.
query = "SELECT name FROM sqlite_master WHERE type='table';"

# 3. Run the query and show the results
tables = pd.read_sql(query, conn)
print("\n--- List of Tables in Chinook ---")
print(tables)
# --- Step 1: Read the 'Track' table ---
print("\n--- Top 5 Tracks ---")
query_tracks = "SELECT * FROM Track LIMIT 5"
df_tracks = pd.read_sql(query_tracks, conn)

# Display specific columns so it fits on your screen
print(df_tracks[['TrackId', 'Name', 'Composer', 'UnitPrice']])
# 4. Close the connection (Good practice!)
# --- Step 2: Filter Data (Expensive Tracks) ---
print("\n--- Tracks costing more than $0.99 ---")
query_expensive = "SELECT Name, UnitPrice FROM Track WHERE UnitPrice > 0.99"
df_expensive = pd.read_sql(query_expensive, conn)

print(df_expensive.head())  # .head() shows just the first 5 rows

# --- Step 3: Joining Tables (Artists + Albums) ---
print("\n--- Artists and their Albums ---")
query_join = """
SELECT Artist.Name as Artist, Album.Title as Album 
FROM Artist
JOIN Album ON Artist.ArtistId = Album.ArtistId
ORDER BY Artist.Name ASC
LIMIT 10
"""
df_join = pd.read_sql(query_join, conn)

print(df_join)
import matplotlib.pyplot as plt  # Add this import at the top if you like, or just here

# --- Step 4: Visualization (Top 10 Genres) ---
print("\n--- Creating Visualization... ---")

# 1. Get data: Count tracks per genre
query_genre = """
SELECT Genre.Name, COUNT(Track.TrackId) as TrackCount
FROM Track
JOIN Genre ON Track.GenreId = Genre.GenreId
GROUP BY Genre.Name
ORDER BY TrackCount DESC
LIMIT 10
"""
df_genre = pd.read_sql(query_genre, conn)

# 2. Setup the plot
plt.figure(figsize=(10, 6))  # Make the figure wide enough
plt.bar(df_genre['Name'], df_genre['TrackCount'], color='skyblue')

# 3. Add labels and title
plt.xlabel('Genre')
plt.ylabel('Number of Tracks')
plt.title('Top 10 Music Genres in Chinook Database')
plt.xticks(rotation=45)  # Rotate genre names so they don't overlap

# 4. Show the plot (or save it)
plt.tight_layout()  # Adjust layout to prevent cutting off labels
plt.show()          # This opens a window with the graph

print("Visualization generated successfully!")
# --- Step 5: Business Analysis (Who spends the most?) ---
print("\n--- Top 5 Customers by Total Spending ---")

query_customers = """
SELECT 
    Customer.FirstName, 
    Customer.LastName, 
    SUM(Invoice.Total) as TotalSpent
FROM Customer
JOIN Invoice ON Customer.CustomerId = Invoice.CustomerId
GROUP BY Customer.CustomerId
ORDER BY TotalSpent DESC
LIMIT 5
"""

df_customers = pd.read_sql(query_customers, conn)

# Print the result nicely
print(df_customers)

# --- Step 6: Visualizing the Money ---
# Let's make a quick bar chart for these customers
plt.figure(figsize=(10, 6))
plt.bar(df_customers['FirstName'], df_customers['TotalSpent'], color='green')
plt.xlabel('Customer Name')
plt.ylabel('Total Money Spent ($)')
plt.title('Top 5 Customers by Sales')
plt.show()

# --- Step 7: Export to CSV ---
print("\n--- Saving report to 'top_customers.csv'... ---")
df_customers.to_csv('top_customers.csv', index=False)
print("File saved successfully!")
conn.close()
