
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

print('code started')
def fetch_google_reviews(url):
    # Set up the Selenium WebDriver
    driver = webdriver.Firefox()  # or use webdriver.Firefox() for Firefox
    driver.get(url)

    # Wait for the page to load
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'review'))
    )

    # # Scroll to load more reviews if necessary
    # for _ in range(3):  # Adjust the range for more scrolls
    #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #     time.sleep(2)  # Wait for new reviews to load
    #     print("wait over")
    # # Find the review elements
    reviews = driver.find_elements(By.CLASS_NAME, 'review')
    print(reviews)
    review_data = []
    for review in reviews:
        try:
            # Extract the reviewer's name
            reviewer_name = review.find_element(By.CLASS_NAME, 'reviewer-name').text.strip() if review.find_element(By.CLASS_NAME, 'reviewer-name') else 'N/A'
            
            # Extract the number of stars
            rating = review.find_element(By.CLASS_NAME, 'rating').text.strip() if review.find_element(By.CLASS_NAME, 'rating') else 'N/A'
            
            # Extract the review text
            review_text = review.find_element(By.CLASS_NAME, 'review-text').text.strip() if review.find_element(By.CLASS_NAME, 'review-text') else 'N/A'
            
            # Extract associated tags (if any)
            tags = [tag.text.strip() for tag in review.find_elements(By.CLASS_NAME, 'tag')]  # Adjust the class name as needed
            tags_str = ', '.join(tags) if tags else 'N/A'
            
            review_data.append({
                'Reviewer Name': reviewer_name,
                'Number of Stars': rating,
                'Review': review_text,
                'Tags': tags_str
            })
        except Exception as e:
            print(f"Error extracting review: {e}")

    driver.quit()  # Close the browser
    return review_data
print('1')
def save_reviews_to_csv(reviews, filename):
    if reviews:  # Check if there are reviews to save
        df = pd.DataFrame(reviews)
        df.to_csv(filename, index=False)
        print(f"Saved {len(reviews)} reviews to {filename}")
    else:
        print("No reviews found to save.")

if __name__ == "__main__":
    # Replace with the actual Google reviews URL
    google_reviews_url = 'https://www.google.com/maps/place/Ulu%E1%B9%9Fu-Kata+Tju%E1%B9%AFa+National+Park/@-25.3126786,131.0223571,10z/data=!3m1!4b1!4m6!3m5!1s0x2b236c2c7ed3b881:0xdb2a86cd5fe91ae4!8m2!3d-25.3437797!4d131.0346514!16zL20vMHBzamM?entry=ttu&g_ep=EgoyMDI1MDkxNC4wIKXMDSoASAFQAw%3D%3D'

