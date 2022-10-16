import sys
if sys.platform == "win32":
    from _ssl import enum_certificates, enum_crls
    

print(enum_certificates("ROOT"))