"""
Training examples for the intent classifier.
Each entry: (question, label)
Labels: "doc", "image", "both"
"""

TRAINING_DATA = [
    # ---- doc examples ----
    ("who is Ayan Aleem", "doc"),
    ("what is his university", "doc"),
    ("what internships has he done", "doc"),
    ("what skills does the resume mention", "doc"),
    ("summarize the document", "doc"),
    ("what does the pdf say about his education", "doc"),
    ("tell me about his work experience", "doc"),
    ("what programming languages does he know", "doc"),
    ("what is mentioned in the resume", "doc"),
    ("give me a summary of the text", "doc"),
    ("what courses has he completed", "doc"),
    ("explain the content of the file", "doc"),
    ("what is his contact information", "doc"),
    ("does the document mention any certifications", "doc"),
    ("what is written on page one", "doc"),
    ("who wrote this document", "doc"),
    ("what topics does the pdf cover", "doc"),
    ("tell me his GPA", "doc"),
    ("what projects are listed", "doc"),
    ("summarize his experience section", "doc"),

    # ---- image examples ----
    ("show me a photo of a person", "image"),
    ("find pictures with flowers", "image"),
    ("do you see any animals in the images", "image"),
    ("which image has a laptop", "image"),
    ("show me pictures of buildings", "image"),
    ("find an image with text in it", "image"),
    ("is there a photo of a car", "image"),
    ("show me the group photo", "image"),
    ("which picture looks like a certificate", "image"),
    ("find images with people smiling", "image"),
    ("show me any nature photos", "image"),
    ("is there a picture of food", "image"),
    ("find the image showing a document scan", "image"),
    ("which photo was taken outdoors", "image"),
    ("show me pictures with multiple people", "image"),
    ("find an image of a phone", "image"),
    ("which image looks like an ID card", "image"),
    ("show me a picture with a certificate in it", "image"),
    ("find any photos of receipts", "image"),
    ("is there an image of a whiteboard", "image"),

    # ---- both examples ----
    ("compare the document with the photo", "both"),
    ("does the image match anything in the resume", "both"),
    ("is the person in the photo the same as in the document", "both"),
    ("compare both the pdf and the images", "both"),
    ("check if the picture relates to the document content", "both"),
    ("cross reference the image with the text", "both"),
    ("does this photo confirm what the document says", "both"),
    ("compare his resume info with the uploaded photo", "both"),
    ("is there a connection between the document and images", "both"),
    ("verify the document using the image", "both"),
    ("match the certificate photo with the resume", "both"),
    ("do the images support what's written in the pdf", "both"),
    ("compare information across document and pictures", "both"),
    ("check both sources together", "both"),
    ("does the photo align with the document's claims", "both"),
]