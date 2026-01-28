import json
import os

def validate_waiver_request(extracted_data):
    """
    Validates extracted waiver details against the SOA database.
    Path: src/utils/validator.py
    """
    soa_db_path = "soa-data-server/soa_database"
    validated_results = []

    for detail in extracted_data.get("waiver_details", []):
        agreement_no = detail["Agreement Number"]
        extracted_waived_amt = float(detail["Total Amount to be Waived off"])
        
        # Construct the path to the specific SOA JSON file
        soa_file_path = os.path.join(soa_db_path, f"{agreement_no}.json")
        
        recommendation = "Waiver should not be approved"
        validation_status = "Failed"
        db_total_overdue = 0

        if os.path.exists(soa_file_path):
            with open(soa_file_path, 'r') as f:
                soa_data = json.load(f)
            
            # Find the total_overdue component in the summary report
            summary_report = soa_data.get("statementOfAccount", {}).get("soa_summary_report", [])
            for component in summary_report:
                if component.get("component") == "total_overdue":
                    db_total_overdue = float(component.get("overdue", 0))
                    break
            
            # Case 1: satisfy condition (Extracted >= DB Overdue)
            if extracted_waived_amt >= db_total_overdue:
                recommendation = "Waiver is approved"
                validation_status = "Passed"
            # Case 2: (Extracted < DB Overdue) handled by default init
        else:
            recommendation = f"Error: SOA file for {agreement_no} not found"

        # Append the validation findings to the detail row
        validated_results.append({
            **detail,
            "database_total_overdue": db_total_overdue,
            "validation_status": validation_status,
            "recommendation": recommendation
        })

    extracted_data["waiver_details"] = validated_results
    return extracted_data