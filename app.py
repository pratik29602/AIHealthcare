from flask import Flask, render_template, request, jsonify
import mysql.connector
import gtts
import playsound
import smtplib
import pywhatkit
import speech_recognition as sr
from datetime import datetime, timedelta
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle
import sys

app = Flask(__name__)
# app.run(port=5001)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'user': 'root',
    'password': 'pratik@123',
    'host': 'localhost',
    'database': 'HealthcareAI'
}


# Load the trained LSTM model and tokenizer
model = load_model('model/intent_model.h5')  # Replace with the path to your model
with open('model/tokenizer.pkl', 'rb') as handle:  # Replace with the path to your tokenizer
    tokenizer = pickle.load(handle)

# Define constants for padding
MAX_SEQUENCE_LENGTH = 50  # Adjust this based on your model's training configuration

def play_voice_response(text):
    """Generate and play a voice response."""
    sound = gtts.gTTS(text, lang='en')
    sound.save("response.mp3")
    playsound.playsound("response.mp3")

# def words_to_number(words):
#     """Convert spoken number words to numeric form."""
#     word_to_digit = {
#         'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
#         'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
#     }
#     print("welcome to w")
#     words = words.split()
#     number = ''.join(word_to_digit.get(word, '') for word in words)
#     return number

chance = 1
def get_voice_input():
    """Capture voice input from the user."""
    global chance
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        print(f"Recognized voice input: {text}")
        return text
    except sr.UnknownValueError:
        if chance < 3:
            play_voice_response('Sorry, I did not understand that. Please try again.')
            chance += 1
            return get_voice_input()
        if chance == 3:
            play_voice_response('You have exceeded the attempt limit. Please try again later.')
            sys.exit()


def send_email(to, subject, body):
    """Send an email using SMTP."""
    sender_email = 'pmane2965@gmail.com'
    sender_password = 'cqaj fosa sllb wayn'  # Use app password for Gmail
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            message = f'Subject: {subject}\n\n{body}'
            server.sendmail(sender_email, to, message)
            print('Mail sent successfully. to -->',to)
            play_voice_response('Report sent to your email successfully.')
    except Exception as e:
        print(f'Failed to send email: {e}')

def preprocess_input(text):
    """Preprocess the text input for LSTM model prediction."""
    sequence = tokenizer.texts_to_sequences([text])
    padded_sequence = pad_sequences(sequence, maxlen=MAX_SEQUENCE_LENGTH)  # Adjust maxlen as needed
    return padded_sequence

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/interaction', methods=['POST'])
def interaction():
    print("wlcome to interaction")
    """Handle user interaction via voice input and respond accordingly."""
    play_voice_response('Hi, how can I help you?')
    user_text = get_voice_input()
    print(f"User input: {user_text}")

    if not user_text:
        play_voice_response('Sorry, I did not understand that. Please try again.')
        get_voice_input()
        return jsonify({'next_action': 'interaction'})

    # Preprocess the input text
    processed_input = preprocess_input(user_text)

    # Predict the intent using the LSTM model
    prediction = model.predict(processed_input)
    intent_index = np.argmax(prediction)

    # Mapping intents to their labels (update these based on your model's training)
    intent_labels = {0: 'request_diagnosis_report', 1: 'request_lab_results', 2: 'general_greeting'}
    intent_label = intent_labels.get(intent_index, 'unknown')

    print(f"Predicted intent: {intent_label}")

    # Define actions based on predicted intent
    if intent_label == 'request_diagnosis_report':
        play_voice_response('Please share your number.')
        
        validate_number()
        return jsonify({'next_action': 'validate_number'})

    elif intent_label == 'request_lab_results':
        play_voice_response('Please provide your patient ID.')
        return jsonify({'next_action': 'validate_number'})
    
    #when patient will ask is pratik mane avilabe on 20 september then modal will (if pratik mane aviabl on 20 septmber )geenerate yes_avilable  then this will match  elif intent_label == 'yes_doctor_avilable':
    elif intent_label == 'yes_doctor_avilable':
        play_voice_response('Doctor is available.')
        return jsonify({'next_action': 'interaction'})

    # Add more conditions for other intents here as needed
    else:
        play_voice_response('Sorry, I cannot process your request right now.')
        return jsonify({'next_action': 'interaction'})

def choose_method(patient_id):
    """Choose the delivery method based on patient confirmation."""

    print("weelcomee to chhose",patient_id)
    confirmation = get_voice_input()
    print("confir-->",confirmation)
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    current_time = datetime.now()
    send_time = current_time + timedelta(minutes=1) 
    send_hour = send_time.hour
    send_minute = send_time.minute

    try:
        cursor.execute("SELECT patient_email FROM patients WHERE patient_number = %s", (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            play_voice_response('Patient number not found. Please try again.')
            return jsonify({'next_action': 'validate_number'})

        patient_email = patient[0]

        if confirmation == 'email' or confirmation == 'Gmail':
            send_email(patient_email, "Your Report", "Here is the report you requested.")
        elif confirmation == 'whatsapp' or confirmation == 'WhatsApp':
            pywhatkit.sendwhatmsg('+7666908802', 'Your report has been sent via WhatsApp!', send_hour, send_minute, wait_time=15)
            play_voice_response('Report sent to your WhatsApp successfully.')
        else:
            play_voice_response('Invalid method selected...')

        return jsonify({'next_action': 'completed'})

    except mysql.connector.Error as err:
        play_voice_response(f'Database error: {err}') 
        return jsonify({'next_action': 'error'})

    finally:
        cursor.close()
        conn.close()

# @app.route('/validate-number', methods=['POST'])
def validate_number():
    """Validate patient number and proceed with the next action."""
    patient_number = get_voice_input()
    print("patient number",patient_number)

    # patient_number = request.json.get('patient_number')
    # print(f"Validating number: {patient_number}")
    

    if not patient_number:
        play_voice_response('Session expired or number not provided, please try again.')
        return jsonify({'next_action': 'interaction'})
    
    play_voice_response(f'Is this your correct number? ')
    play_voice_response(patient_number)
    play_voice_response("say yes  or no")
    confirmation = get_voice_input()  # Capture user's voice response
    print("yes no response-->",confirmation)
    if confirmation in ['yes', 'correct','number is correct']:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM patients WHERE patient_number = %s", (patient_number,))
            patient = cursor.fetchone()

            if not patient:
                play_voice_response('Patient number not found. Please try again.')
                return jsonify({'next_action': 'validate_number'})

            play_voice_response('Choose delivery method: Email or WhatsApp.')
            choose_method(patient_number)
            return jsonify({'next_action': 'choose_method','patient_id': patient_number,'confirmation':confirmation})

        except mysql.connector.Error as err:
            play_voice_response(f'Database error: {err}')
            return jsonify({'next_action': 'error'})

        finally:
            cursor.close()
            conn.close()

    else:
        play_voice_response('Number not confirmed, please try again.')
        get_voice_input()
        return jsonify({'next_action': 'validate_number'})

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)