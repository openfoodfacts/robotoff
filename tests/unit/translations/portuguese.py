import pytest

wrong = ```"Plural-Forms: nplurals=5; plural=(n%10==1 && (n%100!=11 || n%100!=71 || n%100!=91) ? 0 : n%10==2 && (n%100!=12 || n%100!=72 || n%100!=92) ? 1 : ((n%10>=3 && n%10<=4) || n%10==9) && ((n%100 < 10 || n%100 > 19) || (n%100 < 70 || n%100 > 79) || (n%100 < 90 || n%100 > 99)) ? 2 : (n!=0 && n%1;\n"```
right = ```"Plural-Forms: nplurals=5; plural=(n%10==1 && (n%100!=11 || n%100!=71 || n%100!=91) ? 0 : n%10==2 && (n%100!=12 || n%100!=72 || n%100!=92) ? 1 : ((n%10>=3 && n%10<=4) || n%10==9) && ((n%100 < 10 || n%100 > 19) || (n%100 < 70 || n%100 > 79) || (n%100 < 90 || n%100 > 99)) ? 2 : (n!=0 && n%1));\n"```

string1 = right
  
# opening a text file
file1 = open("i18n/br/LC_MESSAGES/robotoff.po", "r")
  
# setting flag and index to 0
flag = 0
index = 0
  
# Loop through the file line by line
for line in file1:  
    index + = 1 
      
    # checking string is present in line or not
    if string1 in line:
        
      flag = 1
      break 
          
# checking condition for string found or not
if flag == 0: 
   print('String', string1 , 'Not Found') 
else: 
   print('String', string1, 'Found In Line', index)
  
# closing text file    
file1.close() 


def test_patterns(text: str, correction: str):
    assert flag !== 0
