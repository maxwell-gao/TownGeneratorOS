#!/usr/bin/env python3
"""
Debug script for step-by-step visualization of town generation.

This script runs each generation step individually and produces SVG
visualizations for debugging purposes.

Usage:
    python debug_generation.py [options]

Options:
    -s, --seed SEED     Random seed (default: 12345)
    -n, --patches N     Number of patches (default: 15)
    -o, --output DIR    Output directory (default: ./debug_output)
    --step N            Run only specific step (1-6)
    --all               Run all steps (default)
"""

import argparse
import sys
import os

# Add town_generator to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from town_generator.step_visualizer import StepVisualizer


def main():
    parser = argparse.ArgumentParser(
        description='Debug town generation with step-by-step visualization'
    )
    parser.add_argument(
        '-s', '--seed',
        type=int,
        default=12345,
        help='Random seed (default: 12345)'
    )
    parser.add_argument(
        '-n', '--patches',
        type=int,
        default=15,
        help='Number of patches/city size (default: 15)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='./debug_output',
        help='Output directory (default: ./debug_output)'
    )
    parser.add_argument(
        '--step',
        type=int,
        default=None,
        help='Run only specific step (1-6)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all steps (default behavior)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Town Generator - Debug Visualization")
    print("=" * 60)
    print(f"Seed: {args.seed}")
    print(f"Patches: {args.patches}")
    print(f"Output: {args.output}")
    print("=" * 60)
    
    # Create visualizer
    vis = StepVisualizer(
        n_patches=args.patches,
        seed=args.seed,
        output_dir=args.output
    )
    
    print(f"\nConfiguration:")
    print(f"  - Plaza needed: {vis.plaza_needed}")
    print(f"  - Citadel needed: {vis.citadel_needed}")
    print(f"  - Walls needed: {vis.walls_needed}")
    print()
    
    step_names = {
        1: "Build Patches (Voronoi tessellation)",
        2: "Optimize Junctions (merge close vertices)",
        3: "Build Walls & Gates",
        4: "Build Streets & Roads",
        5: "Assign Ward Types",
        6: "Generate Building Geometry",
    }
    
    max_retries = 10
    success = False
    for attempt in range(max_retries):
        try:
            if args.step is not None:
                # Run specific step (requires previous steps)
                print(f"Running steps 1 through {args.step}...")
                vis.run_until(args.step)
                print(f"\nStep {args.step}: {step_names.get(args.step, '?')} - Complete")
            else:
                # Run all steps
                for step in range(1, 7):
                    print(f"Step {step}: {step_names.get(step, '?')}...", end=" ", flush=True)
                    vis.run_step(step)
                    print("OK")
            success = True
            break  # Success
        except Exception as e:
            print(f"FAILED: {e}")
            if attempt < max_retries - 1:
                # Retry with different seed
                new_seed = args.seed + attempt + 1
                print(f"\nRetrying with seed {new_seed}...")
                vis = StepVisualizer(
                    n_patches=args.patches,
                    seed=new_seed,
                    output_dir=args.output
                )
                print(f"  New configuration: Plaza={vis.plaza_needed}, Citadel={vis.citadel_needed}, Walls={vis.walls_needed}\n")
            else:
                print(f"\nFailed after {max_retries} attempts")
                import traceback
                traceback.print_exc()
                return 1
    
    if success:
        print("\n" + "=" * 60)
        print("Visualization complete!")
        print(f"Output files saved to: {os.path.abspath(args.output)}")
        print("=" * 60)
        
        # List output files
        print("\nGenerated files:")
        for f in sorted(os.listdir(args.output)):
            if f.endswith('.svg'):
                filepath = os.path.join(args.output, f)
                size = os.path.getsize(filepath)
                print(f"  - {f} ({size:,} bytes)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

