
import base64
def picture_to_base64(filepath):
    try:
        with open(filepath, 'rb') as f:
            base64_data = base64.b64encode(f.read())
            base64_data_str = base64_data.decode("utf-8")
            # print('data:image/jpeg;base64,%s'%base64_data_str)
            f.close()
        return base64_data_str
    except Exception as error:
        print(error)
    return None

pa = r"C:\Users\35906\Desktop\50042420.png"
print(picture_to_base64(pa))