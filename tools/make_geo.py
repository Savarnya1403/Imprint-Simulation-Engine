"""Build the India demographic + geography data pack used by the simulator."""
import json, os

OUT = os.path.join(os.path.dirname(__file__), "..", "app", "data")
os.makedirs(OUT, exist_ok=True)

# Population in millions (2026 projection), urban %, literacy % (Census 2011),
# internet penetration % (composite of TRAI/IAMAI 2025-26), NSDP per capita INR,
# TFR (NFHS-5), sex ratio (Census 2011), region, capital lat/lon.
STATES = [
    # name, pop_m, urban, literacy, internet, pci, tfr, sex_ratio, region, lat, lon, capital
    ("Andhra Pradesh", 53.2, 33.4, 67.0, 58, 219000, 1.7, 993, "south", 15.9129, 79.7400, "Amaravati"),
    ("Arunachal Pradesh", 1.6, 22.9, 65.4, 52, 210000, 2.1, 938, "northeast", 28.2180, 94.7278, "Itanagar"),
    ("Assam", 35.7, 14.1, 72.2, 48, 120000, 1.9, 958, "northeast", 26.2006, 92.9376, "Dispur"),
    ("Bihar", 128.5, 11.3, 61.8, 38, 62000, 3.0, 918, "east", 25.0961, 85.3131, "Patna"),
    ("Chhattisgarh", 30.0, 23.2, 70.3, 45, 130000, 2.0, 991, "central", 21.2787, 81.8661, "Raipur"),
    ("Delhi", 21.5, 97.5, 86.2, 78, 460000, 1.4, 868, "north", 28.6139, 77.2090, "New Delhi"),
    ("Goa", 1.6, 62.2, 88.7, 76, 480000, 1.3, 973, "west", 15.2993, 74.1240, "Panaji"),
    ("Gujarat", 71.5, 42.6, 78.0, 62, 250000, 1.9, 919, "west", 22.2587, 71.1924, "Gandhinagar"),
    ("Haryana", 30.0, 34.9, 75.6, 63, 290000, 2.0, 879, "north", 29.0588, 76.0856, "Chandigarh"),
    ("Himachal Pradesh", 7.5, 10.0, 82.8, 65, 240000, 1.4, 972, "north", 31.1048, 77.1734, "Shimla"),
    ("Jammu & Kashmir", 13.9, 28.5, 67.2, 50, 150000, 1.4, 889, "north", 33.7782, 76.5762, "Srinagar"),
    ("Jharkhand", 38.5, 24.1, 66.4, 42, 105000, 2.3, 948, "east", 23.6102, 85.2799, "Ranchi"),
    ("Karnataka", 68.5, 38.7, 75.4, 64, 330000, 1.6, 973, "south", 15.3173, 75.7139, "Bengaluru"),
    ("Kerala", 35.8, 47.7, 94.0, 82, 280000, 1.5, 1084, "south", 10.8505, 76.2711, "Thiruvananthapuram"),
    ("Madhya Pradesh", 87.0, 27.6, 69.3, 47, 140000, 2.0, 931, "central", 22.9734, 78.6569, "Bhopal"),
    ("Maharashtra", 128.0, 45.2, 82.3, 68, 290000, 1.7, 929, "west", 19.7515, 75.7139, "Mumbai"),
    ("Manipur", 3.2, 30.2, 79.2, 55, 120000, 2.2, 992, "northeast", 24.6637, 93.9063, "Imphal"),
    ("Meghalaya", 3.3, 20.1, 74.4, 48, 130000, 2.9, 989, "northeast", 25.4670, 91.3662, "Shillong"),
    ("Mizoram", 1.2, 52.1, 91.3, 70, 200000, 1.9, 976, "northeast", 23.1645, 92.9376, "Aizawl"),
    ("Nagaland", 2.2, 28.9, 79.6, 52, 150000, 2.7, 931, "northeast", 26.1584, 94.5624, "Kohima"),
    ("Odisha", 46.5, 16.7, 72.9, 48, 130000, 1.8, 979, "east", 20.9517, 85.0985, "Bhubaneswar"),
    ("Punjab", 30.5, 37.5, 75.8, 68, 210000, 1.6, 895, "north", 31.1471, 75.3412, "Chandigarh"),
    ("Rajasthan", 81.0, 24.9, 66.1, 50, 150000, 2.0, 928, "north", 27.0238, 74.2179, "Jaipur"),
    ("Sikkim", 0.68, 25.0, 81.4, 68, 350000, 1.1, 890, "northeast", 27.5330, 88.5122, "Gangtok"),
    ("Tamil Nadu", 77.5, 48.4, 80.1, 72, 320000, 1.4, 996, "south", 11.1271, 78.6569, "Chennai"),
    ("Telangana", 38.5, 38.7, 66.5, 64, 340000, 1.6, 988, "south", 18.1124, 79.0193, "Hyderabad"),
    ("Tripura", 4.1, 26.2, 87.2, 58, 150000, 1.7, 960, "northeast", 23.9408, 91.9882, "Agartala"),
    ("Uttar Pradesh", 240.0, 22.3, 67.7, 45, 85000, 2.4, 912, "north", 26.8467, 80.9462, "Lucknow"),
    ("Uttarakhand", 11.5, 30.2, 78.8, 62, 230000, 1.7, 963, "north", 30.0668, 79.0193, "Dehradun"),
    ("West Bengal", 100.5, 31.9, 76.3, 55, 160000, 1.6, 950, "east", 22.9868, 87.8550, "Kolkata"),
    ("Chandigarh", 1.2, 97.0, 86.4, 80, 400000, 1.4, 818, "north", 30.7333, 76.7794, "Chandigarh"),
    ("Puducherry", 1.6, 68.0, 86.0, 75, 300000, 1.3, 1037, "south", 11.9416, 79.8083, "Puducherry"),
    ("Andaman & Nicobar Island", 0.4, 37.7, 86.3, 65, 250000, 1.5, 876, "east", 11.7401, 92.6586, "Port Blair"),
    ("Ladakh", 0.3, 16.0, 80.0, 45, 180000, 1.3, 800, "north", 34.1526, 77.5771, "Leh"),
    ("Dadara & Nagar Havelli", 0.6, 58.0, 87.0, 65, 350000, 1.4, 930, "west", 20.1809, 73.0169, "Silvassa"),
    ("Lakshadweep", 0.07, 78.0, 91.8, 70, 250000, 1.4, 946, "south", 10.5669, 72.6417, "Kavaratti"),
]

CITIES = {
    "Uttar Pradesh": [("Lucknow", 2), ("Kanpur", 2), ("Varanasi", 2), ("Agra", 2), ("Prayagraj", 2), ("Gorakhpur", 3), ("Bareilly", 3), ("Aligarh", 3), ("Jhansi", 3), ("Sitapur", 4), ("Azamgarh", 4), ("Bahraich", 4), ("Pilibhit", 4)],
    "Maharashtra": [("Mumbai", 1), ("Pune", 1), ("Thane", 1), ("Nagpur", 2), ("Nashik", 2), ("Chhatrapati Sambhajinagar", 3), ("Solapur", 3), ("Kolhapur", 3), ("Nanded", 3), ("Yavatmal", 4), ("Satara", 4), ("Ratnagiri", 4)],
    "Bihar": [("Patna", 2), ("Gaya", 3), ("Bhagalpur", 3), ("Muzaffarpur", 3), ("Darbhanga", 3), ("Purnia", 4), ("Chapra", 4), ("Saharsa", 4), ("Bettiah", 4)],
    "Karnataka": [("Bengaluru", 1), ("Mysuru", 2), ("Hubballi", 2), ("Mangaluru", 2), ("Belagavi", 3), ("Kalaburagi", 3), ("Davanagere", 3), ("Shivamogga", 3), ("Ballari", 4), ("Bidar", 4)],
    "Tamil Nadu": [("Chennai", 1), ("Coimbatore", 2), ("Madurai", 2), ("Tiruchirappalli", 2), ("Salem", 3), ("Tirunelveli", 3), ("Vellore", 3), ("Erode", 3), ("Thanjavur", 4), ("Dindigul", 4)],
    "Telangana": [("Hyderabad", 1), ("Warangal", 2), ("Nizamabad", 3), ("Karimnagar", 3), ("Khammam", 3), ("Mahbubnagar", 4), ("Adilabad", 4)],
    "Andhra Pradesh": [("Visakhapatnam", 2), ("Vijayawada", 2), ("Guntur", 2), ("Tirupati", 3), ("Rajahmundry", 3), ("Kurnool", 3), ("Nellore", 3), ("Anantapur", 4)],
    "West Bengal": [("Kolkata", 1), ("Howrah", 1), ("Siliguri", 2), ("Durgapur", 2), ("Asansol", 3), ("Kharagpur", 3), ("Malda", 3), ("Purulia", 4), ("Murshidabad", 4)],
    "Gujarat": [("Ahmedabad", 1), ("Surat", 1), ("Vadodara", 2), ("Rajkot", 2), ("Bhavnagar", 3), ("Jamnagar", 3), ("Junagadh", 3), ("Anand", 3), ("Bhuj", 4), ("Mehsana", 4)],
    "Rajasthan": [("Jaipur", 1), ("Jodhpur", 2), ("Udaipur", 2), ("Kota", 2), ("Ajmer", 3), ("Bikaner", 3), ("Alwar", 3), ("Bhilwara", 3), ("Barmer", 4), ("Churu", 4)],
    "Madhya Pradesh": [("Indore", 1), ("Bhopal", 1), ("Jabalpur", 2), ("Gwalior", 2), ("Ujjain", 3), ("Sagar", 3), ("Rewa", 3), ("Satna", 3), ("Chhindwara", 4), ("Dhar", 4)],
    "Kerala": [("Kochi", 1), ("Thiruvananthapuram", 1), ("Kozhikode", 2), ("Thrissur", 2), ("Kollam", 3), ("Kannur", 3), ("Alappuzha", 3), ("Palakkad", 3), ("Idukki", 4), ("Wayanad", 4)],
    "Delhi": [("Delhi", 1), ("New Delhi", 1), ("Dwarka", 1), ("Rohini", 1)],
    "Punjab": [("Ludhiana", 2), ("Amritsar", 2), ("Jalandhar", 2), ("Mohali", 2), ("Patiala", 3), ("Bathinda", 3), ("Sangrur", 4)],
    "Haryana": [("Gurugram", 1), ("Faridabad", 1), ("Panipat", 2), ("Ambala", 3), ("Karnal", 3), ("Hisar", 3), ("Rohtak", 3), ("Bhiwani", 4)],
    "Assam": [("Guwahati", 2), ("Dibrugarh", 3), ("Silchar", 3), ("Jorhat", 3), ("Tezpur", 3), ("Nagaon", 4), ("Barpeta", 4)],
    "Odisha": [("Bhubaneswar", 2), ("Cuttack", 2), ("Rourkela", 3), ("Berhampur", 3), ("Sambalpur", 3), ("Puri", 3), ("Koraput", 4), ("Kalahandi", 4)],
    "Jharkhand": [("Ranchi", 2), ("Jamshedpur", 2), ("Dhanbad", 2), ("Bokaro", 3), ("Hazaribagh", 3), ("Deoghar", 3), ("Dumka", 4), ("Chaibasa", 4)],
    "Chhattisgarh": [("Raipur", 2), ("Bhilai", 2), ("Bilaspur", 3), ("Korba", 3), ("Durg", 3), ("Jagdalpur", 4), ("Ambikapur", 4)],
    "Uttarakhand": [("Dehradun", 2), ("Haridwar", 2), ("Rishikesh", 3), ("Haldwani", 3), ("Roorkee", 3), ("Almora", 4), ("Pithoragarh", 4)],
    "Himachal Pradesh": [("Shimla", 2), ("Dharamshala", 3), ("Solan", 3), ("Mandi", 3), ("Kullu", 3), ("Kinnaur", 4)],
    "Jammu & Kashmir": [("Srinagar", 2), ("Jammu", 2), ("Anantnag", 3), ("Baramulla", 3), ("Udhampur", 3), ("Leh", 4), ("Kargil", 4)],
    "Goa": [("Panaji", 1), ("Margao", 3), ("Vasco", 3), ("Mapusa", 3), ("Ponda", 4)],
    "Meghalaya": [("Shillong", 2), ("Tura", 3), ("Jowai", 3), ("Cherrapunji", 4)],
    "Manipur": [("Imphal", 2), ("Thoubal", 3), ("Churachandpur", 4)],
    "Mizoram": [("Aizawl", 2), ("Lunglei", 3), ("Champhai", 4)],
    "Nagaland": [("Kohima", 2), ("Dimapur", 3), ("Mokokchung", 4)],
    "Tripura": [("Agartala", 2), ("Udaipur", 3), ("Dharmanagar", 4)],
    "Arunachal Pradesh": [("Itanagar", 2), ("Naharlagun", 3), ("Pasighat", 4)],
    "Sikkim": [("Gangtok", 2), ("Namchi", 3), ("Mangan", 4)],
    "Chandigarh": [("Chandigarh", 2)],
    "Puducherry": [("Puducherry", 2), ("Karaikal", 3)],
    "Andaman & Nicobar Island": [("Port Blair", 2), ("Havelock", 4)],
    "Ladakh": [("Leh", 2), ("Kargil", 3)],
    "Dadara & Nagar Havelli": [("Silvassa", 3), ("Daman", 3)],
    "Lakshadweep": [("Kavaratti", 3)],
}

NAMES = {
    "north": {
        "male": ["Aarav", "Vivaan", "Aditya", "Rohan", "Arjun", "Kabir", "Ishaan", "Raghav", "Siddharth", "Manish", "Rajesh", "Suresh", "Amit", "Vikram", "Anil", "Deepak", "Harpreet", "Gurpreet", "Jaspreet", "Imran", "Aamir", "Faizan", "Mohit", "Nitin", "Pankaj", "Saurabh", "Shubham", "Yash", "Abhishek", "Rahul", "Varun", "Harsh", "Karan", "Tushar", "Ankit"],
        "female": ["Ananya", "Diya", "Aadhya", "Saanvi", "Myra", "Anika", "Riya", "Priya", "Neha", "Pooja", "Kavita", "Sunita", "Meena", "Ritu", "Shreya", "Nandini", "Simran", "Harleen", "Ayesha", "Fatima", "Zoya", "Sneha", "Divya", "Nisha", "Payal", "Sakshi", "Ishita", "Kritika", "Bhavna", "Rachna", "Poonam", "Suman"],
        "last": ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Kumar", "Mishra", "Tiwari", "Pandey", "Chauhan", "Rathore", "Jain", "Agarwal", "Khan", "Ahmed", "Qureshi", "Gill", "Kaur", "Sandhu", "Bansal", "Saxena", "Srivastava", "Tripathi", "Malhotra", "Kapoor", "Bhatia", "Chawla"],
    },
    "south": {
        "male": ["Karthik", "Vignesh", "Surya", "Praveen", "Arun", "Balaji", "Dinesh", "Ganesh", "Hari", "Kiran", "Manoj", "Naveen", "Ravi", "Sanjay", "Senthil", "Sharath", "Vasanth", "Ajay", "Anand", "Mahesh", "Rajesh", "Sreekant", "Unni", "Appu", "Siddu", "Chandru", "Vijay", "Prasad", "Sudhir", "Ramesh"],
        "female": ["Aishwarya", "Kavya", "Lakshmi", "Meera", "Nithya", "Priyanka", "Ramya", "Sandhya", "Shruti", "Swathi", "Divya", "Gayathri", "Janani", "Keerthana", "Nandini", "Pooja", "Revathi", "Sneha", "Vaishnavi", "Deepa", "Anjali", "Sreelakshmi", "Parvathy", "Bhavana", "Sowmya", "Aparna", "Rekha", "Vani", "Hema"],
        "last": ["Iyer", "Iyengar", "Rao", "Reddy", "Naidu", "Nair", "Menon", "Pillai", "Gowda", "Shetty", "Hegde", "Krishnan", "Subramanian", "Murugan", "Velu", "Choudary", "Prasad", "Varma", "Kumar", "Raj", "Shenoy", "Kamath", "Prabhu", "Bhat", "Acharya"],
    },
    "east": {
        "male": ["Abhijit", "Arindam", "Sourav", "Debashish", "Rajdeep", "Sanjoy", "Arup", "Bikash", "Subrata", "Ranjan", "Manas", "Pritam", "Rakesh", "Santosh", "Bapi", "Tubai", "Ajoy", "Suman", "Pradip", "Sujit", "Debu", "Tapan", "Ashim", "Bishnu", "Ratan"],
        "female": ["Anindita", "Debasmita", "Ipsita", "Moumita", "Payel", "Rupali", "Sohini", "Susmita", "Tanushree", "Bandana", "Jhumpa", "Mousumi", "Priyanka", "Rina", "Sushmita", "Piyali", "Aparna", "Sharmila", "Madhumita", "Rituparna", "Sutapa", "Mamata", "Gita", "Kakali"],
        "last": ["Banerjee", "Chatterjee", "Mukherjee", "Ghosh", "Das", "Dutta", "Sen", "Roy", "Bose", "Pal", "Mondal", "Saha", "Mishra", "Patnaik", "Mohanty", "Behera", "Jena", "Mahapatra", "Pradhan", "Nayak", "Sethi", "Bhattacharya", "Chakraborty", "Bhowmick"],
    },
    "west": {
        "male": ["Jayesh", "Ketan", "Mehul", "Nilesh", "Pankaj", "Rajesh", "Sanjay", "Viral", "Chirag", "Hardik", "Bhavesh", "Dinesh", "Ramesh", "Sagar", "Sameer", "Nandan", "Omkar", "Prashant", "Sachin", "Vinayak", "Amit", "Rohit", "Tejas", "Yash", "Parth"],
        "female": ["Aditi", "Aarti", "Bhakti", "Chaitali", "Deepika", "Hetal", "Jinal", "Komal", "Mansi", "Nandini", "Pooja", "Priyanka", "Rutuja", "Shraddha", "Snehal", "Swara", "Tanvi", "Vaishali", "Gauri", "Mugdha", "Pallavi", "Ashwini", "Manisha", "Rupal", "Krupa"],
        "last": ["Patel", "Shah", "Mehta", "Desai", "Joshi", "Trivedi", "Parmar", "Solanki", "Chavan", "Patil", "Deshmukh", "Jadhav", "Kulkarni", "Shinde", "Gaikwad", "Naik", "Kamat", "Shetty", "Pawar", "Bhosale", "Sawant", "Thakur", "Vaidya", "Gandhi"],
    },
    "northeast": {
        "male": ["Aakash", "Bikash", "Debojit", "Hiren", "Jibon", "Kalyan", "Manash", "Nabajit", "Partha", "Rupam", "Sanjib", "Tanmoy", "Rongsen", "Imkong", "Temjen", "Zubeen", "Bobby", "Lalthan", "Aien", "Kevi"],
        "female": ["Anima", "Bornali", "Doly", "Gitanjali", "Junali", "Kaushiki", "Moushumi", "Namrata", "Pallabi", "Rupali", "Sangita", "Trishna", "Aienla", "Sentila", "Meren", "Lalremsiami", "Zuali", "Ason", "Kevile", "Nzano"],
        "last": ["Das", "Bora", "Baruah", "Gogoi", "Saikia", "Deka", "Hazarika", "Sarma", "Kalita", "Debbarma", "Jamatia", "Sangma", "Marak", "Ao", "Kikon", "Zeliang", "Namchoom", "Chhangte", "Ralte", "Lyngdoh"],
    },
    "central": {
        "male": ["Ajay", "Amit", "Anil", "Arvind", "Ashok", "Deepak", "Dinesh", "Govind", "Hemant", "Jitendra", "Kailash", "Mahesh", "Mukesh", "Naresh", "Pradeep", "Raju", "Ramesh", "Sandeep", "Sunil", "Vijay", "Rahul", "Manish", "Ravi", "Shyam", "Brijesh"],
        "female": ["Aarti", "Anita", "Bharti", "Chhaya", "Durga", "Ganga", "Geeta", "Indu", "Jyoti", "Kalpana", "Kiran", "Lata", "Mamta", "Neelam", "Pinky", "Radha", "Rekha", "Sarita", "Shanti", "Usha", "Sangeeta", "Rani", "Babita", "Kusum", "Shobha"],
        "last": ["Yadav", "Patel", "Sahu", "Verma", "Gupta", "Mishra", "Shukla", "Tiwari", "Pandey", "Singh", "Thakur", "Raikwar", "Ahirwar", "Kushwaha", "Chourasia", "Nema", "Dubey", "Shrivastava", "Jain", "Lodhi"],
    },
}

REGION_OF_STATE = {s[0]: s[8] for s in STATES}

states_json = []
for s in STATES:
    states_json.append({
        "name": s[0], "population_m": s[1], "urban_pct": s[2], "literacy_pct": s[3],
        "internet_pct": s[4], "nsdp_pc": s[5], "tfr": s[6], "sex_ratio": s[7],
        "region": s[8], "lat": s[9], "lon": s[10], "capital": s[11],
        "cities": [{"name": c[0], "tier": c[1]} for c in CITIES.get(s[0], [(s[11], 2)])],
        "map_name": s[0],
    })

json.dump(states_json, open(os.path.join(OUT, "states.json"), "w"), ensure_ascii=False, indent=1)
json.dump(NAMES, open(os.path.join(OUT, "names.json"), "w"), ensure_ascii=False, indent=1)
print("states", len(states_json), "names", sum(len(v["male"]) + len(v["female"]) for v in NAMES.values()))
