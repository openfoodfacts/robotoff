    kcal_matches = regex(text,"/n kcal")
    kJ_matches = regex(text,"/n kJ")
    
    kcal_candidate = max_value(kcal_matches)
    kJ_candidate = max_value(kJ_matches)
    
    stored_value_kcal = product.energy_kcal
    stored_value_kJ = product.energy_kJ

    # Check that the stored values are coherent with the candidates
    if kcal_candidate != stored_value_kcal:
      print "mismatch_kcal_image_stored_kcal"
    if kJ_candidate != stored_value_kJ:
      print "mismatch_kJ_image_stored_kJ"
    
    # If either kcal or kj values are coherent with stored values, try to find the other one
    
    if kcal_candidate = stored_value_kcal:
      # We could add a check between kcal and kJ (kJ/4,184 is roughly equal to kcal)
      if stored_value_kcal is Empty:
        create_insight("kJ_candidate")
        
    if kJ_candidate = stored_value_kJ:
      # We could add a check between kcal and kJ (kJ/4,184 is roughly equal to kcal)
      if stored_value_kJ is Empty:
        create_insight("kcal_candidate")
