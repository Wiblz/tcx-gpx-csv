from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as et
from typing import Final, Union

AttributeNestingLevel = dict[str, Union[str, "AttributeNestingLevel"]]
attributes: Final[AttributeNestingLevel] = {
    'Time': 'Time',
    'Position': {
        'LatitudeDegrees': 'LatitudeDegrees',
        'LongitudeDegrees': 'LongitudeDegrees'
    },
    'AltitudeMeters': 'AltitudeMeters',
    'HeartRateBpm': {
        'Value': 'HRBpm'
    },
    'Cadence': 'Cadence',
    'Extensions': {
        'TPX': {
            'Speed': 'Speed',
            'Watts': 'Watts',
            'Grade': 'Grade'
        }
    }
}


def main(input_file: str, output_file: str):
    try:
        tree = et.parse(input_file)
        root = tree.getroot()
        m = re.match(r'^({.*})', root.tag)
        namespace = m.group(1) if m else ''

        if root.tag != namespace + 'TrainingCenterDatabase':
            print('Unknown root found: ' + root.tag)
            return

        activities = root.find(namespace + 'Activities')
        if activities is None or len(activities) == 0:
            print('Unable to find Activities under root')
            return

        activity = activities.find(namespace + 'Activity')
        if activity is None or len(activity) == 0:
            print('Unable to find Activity under Activities')
            return

        headers: list[str] = []

        def extract_headers(attr_dict: AttributeNestingLevel) -> None:
            for key, value in attr_dict.items():
                if isinstance(value, dict):
                    extract_headers(value)
                else:
                    headers.append(value)

        extract_headers(attributes)

        with open(output_file, 'w') as fout:
            # Write header
            fout.write(','.join(headers) + '\n')

            for lap in activity.iter(namespace + 'Lap'):
                fout.write('New Lap\n')
                for track in lap.iter(namespace + 'Track'):
                    fout.write('New Track\n')
                    for trackpoint in track.iter(namespace + 'Trackpoint'):
                        data = extract_trackpoint_data(trackpoint)
                        fout.write(','.join(data) + '\n')

    except Exception as e:
        print(f"Error processing file: {e}")


def extract_trackpoint_data(trackpoint: et.Element | None,
                            attrs: AttributeNestingLevel | None = None) -> list[str]:
    """
    Extract data fields from a trackpoint element based on configurable attributes.

    Args:
        trackpoint: XML trackpoint element
        attrs: Optional dictionary of attributes to extract (uses global attributes if None)

    Returns:
        List of extracted values in the order they appear in the attributes dictionary
    """
    if attrs is None:
        attrs = attributes

    namespace = "{*}" # Ignore namespaces

    # Recursive function to extract nested attributes
    def extract_attribute(element: et.Element | None, attr_dict: AttributeNestingLevel) -> list[str]:
        results: list[str] = []

        for key, value in attr_dict.items():
            if isinstance(value, dict):
                # Handle nested attributes
                child = element.find(namespace + key) if element is not None else None
                results.extend(extract_attribute(child, value))
            else:
                # Extract leaf attribute
                results.append(get_element_text(element, namespace + key))

        return results

    extracted_values = extract_attribute(trackpoint, attrs)

    # The main function should be updated to use these headers for the CSV header row
    return extracted_values


def get_element_text(element: et.Element | None, tag: str) -> str:
    """Safely extract text from an XML element."""
    if element is None:
        return ''
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else ''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert TCX files to CSV format.')
    parser.add_argument('input', help='input TCX file')
    parser.add_argument('output', help='output CSV file')
    args = parser.parse_args()

    main(args.input, args.output)
