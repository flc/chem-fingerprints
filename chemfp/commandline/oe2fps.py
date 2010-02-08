import sys
import textwrap
from chemfp import argparse

from chemfp import shared
from chemfp import openeye as oe


##### Handle command-line argument parsing

# Build up some help text based on the atype and btype fields
atype_options = "\n  ".join(textwrap.wrap(" ".join(sorted(oe._atypes))))
btype_options = "\n  ".join(textwrap.wrap(" ".join(sorted(oe._btypes))))

# Extra help text after the parameter descriptions
epilog = """\

ATYPE is one or more of the following, separated by commas
  {atype_options}
Examples:
  --atype DefaultAtom
  --atype AtomicNumber,HvyDegree

BTYPE is one or more of the following, separated by commas
  {btype_options}
Examples:
  --btype DefaultBond,Chiral
  --btype BondOrder

OEChem guesses the input structure format based on the filename
extension and assumes SMILES for structures read from stdin.
Use "--in FORMAT" to select an alternative, where FORMAT is one of:
 
  File Type      Valid FORMATs (use gz if compressed)
  ---------      ------------------------------------
   SMILES        smi, ism, can, smi.gz, ism.gz, can.gz
   SDF           sdf, mol, sdf.gz, mol.gz
   SKC           skc, skc.gz
   CDK           cdk, cdk.gz
   MOL2          mol2, mol2.gz
   PDB           pdb, ent, pdb.gz, ent.gz
   MacroModel    mmod, mmod.gz
   OEBinary v2   oeb, oeb.gz
   old OEBinary  bin
""".format(atype_options=atype_options,
           btype_options=btype_options)

parser = argparse.ArgumentParser(
    description="Generate FPS fingerprints from a structure file using OEChem",
    epilog=epilog,
    formatter_class=argparse.RawDescriptionHelpFormatter,    
    )
path_group = parser.add_argument_group("path fingerprints")
path_group.add_argument(
    "--path", action="store_true", help="generate path fingerprints (default)")
path_group.add_argument(
    "--num-bits", type=int, metavar="INT",
    help="number of bits in the path fingerprint (default=4096)", default=4096)
path_group.add_argument(
    "--min-bonds", type=int, metavar="INT",
    help="minimum number of bonds in path (default=0)", default=0)
path_group.add_argument(
    "--max-bonds", type=int, metavar="INT",
    help="maximum number of bonds in path (default=5)", default=5)
path_group.add_argument(
    "--atype", help="atom type (default=DefaultAtom)", default="DefaultAtom")
path_group.add_argument(
    "--btype", help="bond type (default=DefaultBond)", default="DefaultBond")

maccs_group = parser.add_argument_group("166 bit MACCS substructure keys")
maccs_group.add_argument(
    "--maccs166", action="store_true", help="generate MACCS fingerprints")

parser.add_argument(
    "--in", metavar="FORMAT", dest="format",
    help="input structure format (default guesses from filename)")
parser.add_argument(
    "-o", "--output", metavar="FILENAME",
    help="save the fingerprints to FILENAME (default=stdout)")
parser.add_argument(
    "filename", nargs="?", help="input structure file (default is stdin)", default=None)


#######

def main(args=None):
    args = parser.parse_args(args)
    outfile = sys.stdout

    if args.maccs166:
        if args.path:
            parser.error("Cannot specify both --maccs166 and --path")
        # Create the MACCS keys fingerprinter
        fingerprinter = get_maccs_fingerprinter()
        num_bits = 166
        params = "OpenEye-MACCS166/1"
    else:
        if not (16 <= args.num_bits <= 65536):
            parser.error("--num-bits must be between 16 and 65536 bits")
        num_bits = args.num_bits

        if not (0 <= args.min_bonds):
            parser.error("--min-bonds must be 0 or greater")
        if not (args.min_bonds <= args.max_bonds):
            parser.error("--max-bonds must not be smaller than --min-bonds")

        # Parse the arguments
        atype = oe.atom_description_to_value(args.atype)
        btype = oe.bond_description_to_value(args.btype)

        # Create the normalized string form
        atype_string = oe.atom_value_to_description(atype)
        btype_string = oe.bond_value_to_description(btype)


        params = oe.format_path_params(min_bonds=args.min_bonds,
                                       max_bonds=args.max_bonds,
                                       atype=atype_string,
                                       btype=btype_string)

        # Create the path fingerprinter
        fingerprinter = oe.get_path_fingerprinter(
            num_bits=num_bits,
            min_bonds=args.min_bonds,
            max_bonds=args.max_bonds,
            atype=atype,
            btype=btype)

    # Ready the input reader/iterator
    reader = oe.read_structures(args.filename, args.format)

    shared.generate_fpsv1_output(dict(num_bits=num_bits,
                                      software=oe.SOFTWARE,
                                      source=args.filename,
                                      params=params),
                                 reader,
                                 fingerprinter,
                                 args.output)

if __name__ == "__main__":
    main()