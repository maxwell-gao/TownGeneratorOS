#!/usr/bin/env python3
"""
Main entry point for Town Generator
"""
import argparse
import sys
from town_generator.model import Model
from town_generator.export import export_to_json


def main():
    parser = argparse.ArgumentParser(description='Medieval Fantasy City Generator - Python Port')
    parser.add_argument('-s', '--size', type=int, default=15, 
                       help='City size (6=Small Town, 10=Large Town, 15=Small City, 24=Large City, 40=Metropolis)')
    parser.add_argument('--seed', type=int, default=-1,
                       help='Random seed (-1 for random)')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output JSON file (default: print to stdout)')
    parser.add_argument('--indent', type=int, default=2,
                       help='JSON indentation (default: 2)')
    
    args = parser.parse_args()
    
    # Validate size
    if args.size < 6:
        print("Warning: Size too small, using 6", file=sys.stderr)
        args.size = 6
    elif args.size > 40:
        print("Warning: Size too large, using 40", file=sys.stderr)
        args.size = 40
    
    try:
        print(f"Generating city (size={args.size}, seed={args.seed if args.seed != -1 else 'random'})...", 
              file=sys.stderr)
        
        model = Model(args.size, args.seed)
        
        print(f"City generated successfully!", file=sys.stderr)
        print(f"  Patches: {len(model.patches)}", file=sys.stderr)
        print(f"  Inner patches: {len(model.inner)}", file=sys.stderr)
        print(f"  Gates: {len(model.gates)}", file=sys.stderr)
        print(f"  Streets: {len(model.streets)}", file=sys.stderr)
        print(f"  Roads: {len(model.roads)}", file=sys.stderr)
        print(f"  Seed: {model.to_dict()['seed']}", file=sys.stderr)
        
        json_str = export_to_json(model, args.output, args.indent)
        
        if args.output:
            print(f"Exported to {args.output}", file=sys.stderr)
        else:
            print(json_str)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
