#!/usr/bin/env python3
"""Build script for SES Stakeholder Summit Portal.

Reads stakeholder markdown files and config.yaml, generates a static HTML site.
"""

import os
import re
import json
import shutil
import yaml
from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
STAKEHOLDER_DIR = os.path.join(CONTENT_DIR, 'stakeholders')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')


def load_config():
    """Load the config.yaml file."""
    with open(os.path.join(CONTENT_DIR, 'config.yaml'), 'r') as f:
        return yaml.safe_load(f)


def parse_stakeholder_file(filepath):
    """Parse a stakeholder markdown file into a list of stakeholder dicts.

    Handles two formats:
    1. Single-line: **Field:** value1; value2; value3
    2. Multi-line:  **Field:**
                    - bullet 1
                    - bullet 2
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Split by --- separator (used consistently across all files)
    raw_sections = re.split(r'\n---\s*\n', content)

    stakeholders = []
    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        # Skip sections that don't contain stakeholder fields
        if '**Role/Title' not in section and '**Who they represent' not in section:
            continue

        sh = {}

        # Extract fields using a multi-line aware approach
        sh['role_title'] = extract_field(section, 'Role/Title')
        sh['who_they_represent'] = extract_field(section, 'Who they represent')

        raw_interests = extract_field(section, 'Primary Interests')
        if raw_interests:
            sh['primary_interests'] = split_to_bullets(raw_interests)

        # Key Concerns has variable suffix like "(extraction/production stage)"
        raw_concerns = extract_field_fuzzy(section, 'Key Concerns')
        if raw_concerns:
            sh['key_concerns'] = split_to_bullets(raw_concerns)

        sh['likely_allies'] = extract_field(section, 'Likely Allies') or ''
        sh['likely_opponents'] = extract_field(section, 'Likely Opponents') or ''

        if sh.get('role_title') or sh.get('who_they_represent'):
            stakeholders.append(sh)

    return stakeholders


def extract_field(section, field_name):
    """Extract a field value from a markdown section.

    Handles both inline values and multi-line bullet lists.
    """
    # Pattern: **Field Name:** or **Field Name**: (with optional markdown formatting)
    pattern = rf'\*\*{re.escape(field_name)}[\*:]*\*?\*?\s*[:]*\s*'
    m = re.search(pattern, section)
    if not m:
        return None

    # Get everything after the field label
    rest = section[m.end():]

    # Find the end of this field (next **Field** marker or end of section)
    end_match = re.search(r'\n\s*\*\*[A-Z]', rest)
    if end_match:
        value = rest[:end_match.start()]
    else:
        value = rest

    return value.strip().rstrip('*')


def extract_field_fuzzy(section, field_prefix):
    """Extract a field whose name starts with field_prefix (e.g., 'Key Concerns')."""
    pattern = rf'\*\*{re.escape(field_prefix)}[^*]*\*\*\s*[:]*\s*'
    m = re.search(pattern, section)
    if not m:
        return None

    rest = section[m.end():]
    end_match = re.search(r'\n\s*\*\*[A-Z]', rest)
    if end_match:
        value = rest[:end_match.start()]
    else:
        value = rest

    return value.strip().rstrip('*')


def split_to_bullets(text):
    """Split field text into a list of bullets.

    Handles:
    - Semicolon-separated on one line: "item1; item2; item3"
    - Multi-line bullet list: "\\n- item1\\n- item2\\n- item3"
    - Mix of both
    """
    lines = text.strip().split('\n')

    # Check if this is a multi-line bullet list
    bullet_lines = [line.strip() for line in lines if line.strip().startswith('- ')]

    if bullet_lines:
        # Multi-line format: each line starting with "- " is a bullet
        items = [line.lstrip('- ').strip() for line in bullet_lines]
    elif ';' in text:
        # Semicolon-separated format
        items = [item.strip() for item in text.split(';') if item.strip()]
    else:
        # Single item
        items = [text.strip()]

    # Clean up items
    cleaned = []
    for item in items:
        item = item.strip()
        if item.startswith('- '):
            item = item[2:]
        # Capitalize first letter
        if item and item[0].islower():
            item = item[0].upper() + item[1:]
        if item:
            cleaned.append(item)

    return cleaned


def build_site(config):
    """Generate the full static site."""
    # Set up Jinja2
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=False,
    )

    # Clean and recreate output directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Copy static assets
    for subdir in ['css', 'js']:
        src = os.path.join(TEMPLATE_DIR, subdir)
        dst = os.path.join(OUTPUT_DIR, subdir)
        if os.path.exists(src):
            shutil.copytree(src, dst)

    # Build portal landing page
    portal_tmpl = env.get_template('portal-landing.html')
    html = portal_tmpl.render(
        site=config['site'],
        categories=config['categories'],
    )
    write_file(os.path.join(OUTPUT_DIR, 'index.html'), html)
    print(f"  Built: index.html")

    # Build each category
    category_tmpl = env.get_template('category-landing.html')
    role_tmpl = env.get_template('role-page.html')

    total_roles = 0

    for cat in config['categories']:
        cat_dir = os.path.join(OUTPUT_DIR, cat['id'])
        os.makedirs(cat_dir, exist_ok=True)

        # Parse the stakeholder markdown
        source_path = os.path.join(STAKEHOLDER_DIR, cat['source_file'])
        parsed = parse_stakeholder_file(source_path)

        if len(parsed) != len(cat['stakeholders']):
            print(f"  WARNING: {cat['id']} — config has {len(cat['stakeholders'])} stakeholders "
                  f"but parsed {len(parsed)} from markdown")

        # Merge parsed content with config metadata
        stakeholder_data = []
        for i, sh_config in enumerate(cat['stakeholders']):
            sh_parsed = parsed[i] if i < len(parsed) else {}
            merged = {**sh_config, **sh_parsed}
            stakeholder_data.append(merged)

        # Build category landing
        html = category_tmpl.render(
            site=config['site'],
            category=cat,
            stakeholders=stakeholder_data,
        )
        write_file(os.path.join(cat_dir, 'index.html'), html)
        print(f"  Built: {cat['id']}/index.html ({len(stakeholder_data)} roles)")

        # Build each role page
        for sh in stakeholder_data:
            # Build coalition data for post-summit reveal (JSON embedded in page)
            coalition_data = {
                'allies': sh.get('likely_allies', ''),
                'opponents': sh.get('likely_opponents', ''),
            }

            # Other stakeholders in same category (for coalition prediction UI)
            other_stakeholders = [s for s in stakeholder_data if s['id'] != sh['id']]

            html = role_tmpl.render(
                site=config['site'],
                category=cat,
                stakeholder=sh,
                other_stakeholders=other_stakeholders,
                all_stakeholders=stakeholder_data,
                coalition_data_json=json.dumps(coalition_data),
            )
            write_file(os.path.join(cat_dir, f"{sh['id']}.html"), html)
            total_roles += 1

    print(f"\nDone! Generated {total_roles} role pages + "
          f"{len(config['categories'])} category pages + 1 portal landing "
          f"= {total_roles + len(config['categories']) + 1} total pages")


def write_file(path, content):
    """Write content to a file, creating directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


def main():
    print("SES Stakeholder Summit Portal — Build\n")

    config = load_config()
    print(f"Loaded config: {len(config['categories'])} categories, "
          f"{sum(len(c['stakeholders']) for c in config['categories'])} stakeholders\n")

    build_site(config)


if __name__ == '__main__':
    main()
