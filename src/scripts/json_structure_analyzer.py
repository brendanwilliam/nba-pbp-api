#!/usr/bin/env python3
"""
JSON Structure Analyzer for NBA Game Data
Analyzes JSON structure evolution across different seasons and identifies schema changes
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime
import re

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class JSONStructureAnalyzer:
    """Analyze JSON structure patterns and evolution across NBA seasons"""
    
    def __init__(self, data_dir: str = "tests/data"):
        self.data_dir = Path(data_dir)
        self.files_by_season = {}
        self.season_order = []
        self.structure_cache = {}
        
    def load_and_categorize_files(self):
        """Load and categorize JSON files by season and type"""
        json_files = list(self.data_dir.glob("*.json"))
        
        # Filter out the existing files and only process the extracted samples
        sample_files = [f for f in json_files if re.match(r'\d{6}_(reg|pla)_', f.name)]
        
        print(f"Found {len(sample_files)} NBA game sample files")
        
        for file_path in sample_files:
            # Parse filename: 199697_reg_NYK-vs-BOS_0110_0029600481.json
            parts = file_path.stem.split('_')
            if len(parts) >= 2:
                season_code = parts[0]  # 199697
                game_type = parts[1]    # reg or pla
                
                # Convert season code to readable format
                year1 = season_code[:4]
                year2 = season_code[4:]
                season = f"{year1}-{year2}"
                
                if season not in self.files_by_season:
                    self.files_by_season[season] = {'regular': [], 'playoff': []}
                    
                file_type = 'regular' if game_type == 'reg' else 'playoff'
                self.files_by_season[season][file_type].append(file_path)
        
        # Sort seasons chronologically
        self.season_order = sorted(self.files_by_season.keys())
        print(f"Seasons with data: {len(self.season_order)} ({self.season_order[0]} to {self.season_order[-1]})")
        
    def extract_json_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Recursively extract structure information from JSON data"""
        if isinstance(data, dict):
            structure = {
                "_type": "object",
                "_keys": set(data.keys()),
                "_key_count": len(data.keys())
            }
            
            for key, value in data.items():
                key_path = f"{path}.{key}" if path else key
                structure[key] = self.extract_json_structure(value, key_path)
                
            return structure
            
        elif isinstance(data, list):
            structure = {
                "_type": "array",
                "_length": len(data),
                "_item_types": set()
            }
            
            # Analyze first few items to understand array structure
            sample_items = data[:3] if len(data) > 3 else data
            for i, item in enumerate(sample_items):
                item_structure = self.extract_json_structure(item, f"{path}[{i}]")
                structure[f"_item_{i}"] = item_structure
                structure["_item_types"].add(item_structure.get("_type", type(item).__name__))
                
            return structure
            
        else:
            return {
                "_type": type(data).__name__,
                "_value_type": self._get_value_type(data)
            }
    
    def _get_value_type(self, value: Any) -> str:
        """Get more specific type information for primitive values"""
        if isinstance(value, str):
            if value.isdigit():
                return "numeric_string"
            elif re.match(r'\d{4}-\d{2}-\d{2}', value):
                return "date_string"
            elif re.match(r'\d{2}:\d{2}', value):
                return "time_string"
            else:
                return "string"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif value is None:
            return "null"
        else:
            return type(value).__name__
    
    def analyze_file_structure(self, file_path: Path) -> Dict[str, Any]:
        """Analyze structure of a single JSON file"""
        if str(file_path) in self.structure_cache:
            return self.structure_cache[str(file_path)]
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            structure = self.extract_json_structure(data)
            
            # Add metadata
            structure["_metadata"] = {
                "file_path": str(file_path),
                "file_size_mb": file_path.stat().st_size / (1024 * 1024),
                "analyzed_at": datetime.now().isoformat()
            }
            
            self.structure_cache[str(file_path)] = structure
            return structure
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {"_error": str(e)}
    
    def compare_structures(self, struct1: Dict[str, Any], struct2: Dict[str, Any], path: str = "") -> List[str]:
        """Compare two JSON structures and identify differences"""
        differences = []
        
        # Compare types
        type1 = struct1.get("_type")
        type2 = struct2.get("_type")
        
        if type1 != type2:
            differences.append(f"{path}: Type changed from {type1} to {type2}")
            return differences  # Don't dive deeper if types are different
        
        if type1 == "object":
            keys1 = struct1.get("_keys", set())
            keys2 = struct2.get("_keys", set())
            
            # New keys
            new_keys = keys2 - keys1
            if new_keys:
                differences.append(f"{path}: New keys added: {sorted(new_keys)}")
            
            # Removed keys
            removed_keys = keys1 - keys2
            if removed_keys:
                differences.append(f"{path}: Keys removed: {sorted(removed_keys)}")
            
            # Compare common keys
            common_keys = keys1 & keys2
            for key in common_keys:
                if key in struct1 and key in struct2 and not key.startswith("_"):
                    key_path = f"{path}.{key}" if path else key
                    key_diffs = self.compare_structures(struct1[key], struct2[key], key_path)
                    differences.extend(key_diffs)
        
        elif type1 == "array":
            # Compare array item types
            types1 = struct1.get("_item_types", set())
            types2 = struct2.get("_item_types", set())
            
            if types1 != types2:
                differences.append(f"{path}: Array item types changed from {types1} to {types2}")
        
        return differences
    
    def analyze_season_evolution(self) -> Dict[str, Any]:
        """Analyze how JSON structure evolved across seasons"""
        print("\nAnalyzing JSON structure evolution across seasons...")
        
        evolution = {
            "seasons_analyzed": [],
            "major_changes": {},
            "field_evolution": defaultdict(list),
            "structure_complexity": {},
            "error_files": []
        }
        
        previous_structure = None
        previous_season = None
        
        for season in self.season_order:
            print(f"  Analyzing {season}...")
            season_files = self.files_by_season[season]
            
            # Analyze regular season games first
            if season_files['regular']:
                sample_file = season_files['regular'][0]  # Use first regular season game
                structure = self.analyze_file_structure(sample_file)
                
                if "_error" in structure:
                    evolution["error_files"].append(f"{season}: {structure['_error']}")
                    continue
                
                evolution["seasons_analyzed"].append(season)
                
                # Calculate structure complexity
                complexity = self._calculate_structure_complexity(structure)
                evolution["structure_complexity"][season] = complexity
                
                # Compare with previous season
                if previous_structure is not None:
                    differences = self.compare_structures(previous_structure, structure)
                    if differences:
                        evolution["major_changes"][f"{previous_season} → {season}"] = differences
                
                previous_structure = structure
                previous_season = season
        
        return evolution
    
    def _calculate_structure_complexity(self, structure: Dict[str, Any]) -> Dict[str, int]:
        """Calculate complexity metrics for a JSON structure"""
        complexity = {
            "total_fields": 0,
            "nested_objects": 0,
            "arrays": 0,
            "max_depth": 0
        }
        
        def count_recursive(data: Dict[str, Any], depth: int = 0) -> None:
            complexity["max_depth"] = max(complexity["max_depth"], depth)
            
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                    
                complexity["total_fields"] += 1
                
                if isinstance(value, dict):
                    if value.get("_type") == "object":
                        complexity["nested_objects"] += 1
                        count_recursive(value, depth + 1)
                    elif value.get("_type") == "array":
                        complexity["arrays"] += 1
        
        count_recursive(structure)
        return complexity
    
    def analyze_key_patterns(self) -> Dict[str, Any]:
        """Analyze common key patterns across all files"""
        print("\nAnalyzing key patterns across all seasons...")
        
        all_keys = defaultdict(list)  # key -> [seasons where it appears]
        key_types = defaultdict(Counter)  # key -> {type: count}
        
        for season in self.season_order:
            season_files = self.files_by_season[season]
            
            # Analyze both regular and playoff games
            for file_type, files in season_files.items():
                for file_path in files:
                    structure = self.analyze_file_structure(file_path)
                    if "_error" in structure:
                        continue
                    
                    keys_in_file = self._extract_all_keys(structure)
                    for key, key_type in keys_in_file:
                        all_keys[key].append(season)
                        key_types[key][key_type] += 1
        
        # Analyze patterns
        patterns = {
            "universal_keys": [],     # Keys present in all seasons
            "deprecated_keys": [],    # Keys that disappeared
            "new_keys_by_season": {}, # Keys that appeared in specific seasons
            "inconsistent_types": {}  # Keys with multiple types
        }
        
        total_seasons = len(self.season_order)
        
        for key, seasons in all_keys.items():
            unique_seasons = set(seasons)
            
            # Universal keys (in most seasons)
            if len(unique_seasons) >= total_seasons * 0.8:
                patterns["universal_keys"].append(key)
            
            # Check for type inconsistencies
            types_for_key = key_types[key]
            if len(types_for_key) > 1:
                patterns["inconsistent_types"][key] = dict(types_for_key)
            
            # Find when keys first appeared
            first_season = min(unique_seasons, key=lambda x: self.season_order.index(x))
            if first_season not in patterns["new_keys_by_season"]:
                patterns["new_keys_by_season"][first_season] = []
            patterns["new_keys_by_season"][first_season].append(key)
        
        return patterns
    
    def _extract_all_keys(self, structure: Dict[str, Any], prefix: str = "") -> List[Tuple[str, str]]:
        """Extract all keys from a structure with their types"""
        keys = []
        
        for key, value in structure.items():
            if key.startswith("_"):
                continue
                
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                value_type = value.get("_type", "unknown")
                keys.append((full_key, value_type))
                
                # Recurse into nested objects
                if value_type == "object":
                    nested_keys = self._extract_all_keys(value, full_key)
                    keys.extend(nested_keys)
        
        return keys
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive analysis report"""
        print("🔍 NBA JSON Structure Analysis")
        print("=" * 80)
        
        # Load and categorize files
        self.load_and_categorize_files()
        
        if not self.files_by_season:
            return {"error": "No valid JSON sample files found"}
        
        # Perform analyses
        evolution_analysis = self.analyze_season_evolution()
        key_patterns = self.analyze_key_patterns()
        
        # Sample structure analysis
        sample_structures = {}
        for season in self.season_order[:3]:  # First 3 seasons
            files = self.files_by_season[season]['regular']
            if files:
                sample_structures[season] = self.analyze_file_structure(files[0])
        
        report = {
            "analysis_metadata": {
                "total_files_analyzed": sum(
                    len(files['regular']) + len(files['playoff']) 
                    for files in self.files_by_season.values()
                ),
                "seasons_covered": len(self.season_order),
                "season_range": f"{self.season_order[0]} to {self.season_order[-1]}",
                "analyzed_at": datetime.now().isoformat()
            },
            "evolution_analysis": evolution_analysis,
            "key_patterns": key_patterns,
            "sample_structures": sample_structures
        }
        
        return report
    
    def print_summary_report(self, report: Dict[str, Any]):
        """Print a human-readable summary of the analysis"""
        print("\n📊 ANALYSIS SUMMARY")
        print("=" * 80)
        
        metadata = report["analysis_metadata"]
        print(f"Files analyzed: {metadata['total_files_analyzed']}")
        print(f"Seasons covered: {metadata['seasons_covered']} ({metadata['season_range']})")
        
        # Evolution summary
        evolution = report["evolution_analysis"]
        print(f"\n🔄 STRUCTURE EVOLUTION")
        print(f"Seasons successfully analyzed: {len(evolution['seasons_analyzed'])}")
        print(f"Major structural changes detected: {len(evolution['major_changes'])}")
        
        if evolution["major_changes"]:
            print(f"\nKey structural changes:")
            for transition, changes in list(evolution["major_changes"].items())[:5]:
                print(f"  {transition}:")
                for change in changes[:3]:  # Show first 3 changes
                    print(f"    • {change}")
                if len(changes) > 3:
                    print(f"    ... and {len(changes) - 3} more changes")
        
        # Key patterns summary
        patterns = report["key_patterns"]
        print(f"\n🔑 KEY PATTERNS")
        print(f"Universal keys (in 80%+ of seasons): {len(patterns['universal_keys'])}")
        print(f"Keys with inconsistent types: {len(patterns['inconsistent_types'])}")
        
        if patterns["inconsistent_types"]:
            print(f"\nType inconsistencies (showing first 5):")
            for key, types in list(patterns["inconsistent_types"].items())[:5]:
                print(f"  {key}: {dict(types)}")
        
        # Complexity trends
        if evolution["structure_complexity"]:
            print(f"\n📈 COMPLEXITY TRENDS")
            first_season = self.season_order[0]
            last_season = self.season_order[-1]
            
            if first_season in evolution["structure_complexity"] and last_season in evolution["structure_complexity"]:
                first_complexity = evolution["structure_complexity"][first_season]
                last_complexity = evolution["structure_complexity"][last_season]
                
                print(f"Total fields: {first_complexity['total_fields']} → {last_complexity['total_fields']}")
                print(f"Nested objects: {first_complexity['nested_objects']} → {last_complexity['nested_objects']}")
                print(f"Arrays: {first_complexity['arrays']} → {last_complexity['arrays']}")
                print(f"Max depth: {first_complexity['max_depth']} → {last_complexity['max_depth']}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze NBA JSON structure evolution')
    parser.add_argument('--data-dir', type=str, default='tests/data',
                       help='Directory containing JSON sample files')
    parser.add_argument('--output-file', type=str,
                       help='Save full analysis report to JSON file')
    parser.add_argument('--summary-only', action='store_true',
                       help='Show only summary, not full analysis')
    
    args = parser.parse_args()
    
    analyzer = JSONStructureAnalyzer(args.data_dir)
    
    try:
        report = analyzer.generate_comprehensive_report()
        
        if "error" in report:
            print(f"Error: {report['error']}")
            return
        
        # Print summary
        analyzer.print_summary_report(report)
        
        # Save full report if requested
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n💾 Full analysis report saved to: {args.output_file}")
        
        # Show detailed analysis if not summary-only
        if not args.summary_only:
            print(f"\n📋 For detailed analysis, run with --output-file option")
            
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
    except Exception as e:
        print(f"Error during analysis: {e}")


if __name__ == "__main__":
    main()