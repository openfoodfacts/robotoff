In order to install ORTools had to update tritonclient as that depended on an older version of protobuf:

poetry add tritonclient@latest

then

poetry add ortools

