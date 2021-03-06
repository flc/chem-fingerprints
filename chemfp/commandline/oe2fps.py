from __future__ import absolute_import
import sys
import itertools
import textwrap

from .. import ParseError
from .. import argparse, types, io
from .. import openeye as oe
from . import cmdsupport

##### Handle command-line argument parsing

# Build up some help text based on the atype and btype fields
atype_options = "\n  ".join(textwrap.wrap(" ".join(sorted(oe._atypes))))
btype_options = "\n  ".join(textwrap.wrap(" ".join(sorted(oe._btypes))))

# Extra help text after the parameter descriptions
epilog = """\

ATYPE is one or more of the following, separated by commas
  %(atype_options)s
Examples:
  --atype DefaultAtom
  --atype AtomicNumber,HvyDegree

BTYPE is one or more of the following, separated by commas
  %(btype_options)s
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
""" % dict(atype_options=atype_options,
           btype_options=btype_options)

parser = argparse.ArgumentParser(
    description="Generate FPS fingerprints from a structure file using OEChem",
    epilog=epilog,
    formatter_class=argparse.RawDescriptionHelpFormatter,    
    )
path_group = parser.add_argument_group("path fingerprints")
path_group.add_argument(
    "--path", action="store_true", help="generate path fingerprints (default)")

PathFamily = oe.OpenEyePathFingerprintFamily_v1
PathFamily.add_argument_to_argparse("numbits", path_group)
PathFamily.add_argument_to_argparse("minbonds", path_group)
PathFamily.add_argument_to_argparse("maxbonds", path_group)
PathFamily.add_argument_to_argparse("atype", path_group)
PathFamily.add_argument_to_argparse("btype", path_group)

maccs_group = parser.add_argument_group("166 bit MACCS substructure keys")
maccs_group.add_argument(
    "--maccs166", action="store_true", help="generate MACCS fingerprints")

substruct_group = parser.add_argument_group("881 bit ChemFP substructure keys")
substruct_group.add_argument(
    "--substruct", action="store_true", help="generate ChemFP substructure fingerprints")

rdmaccs_group = parser.add_argument_group("ChemFP version of the 166 bit RDKit/MACCS keys")
rdmaccs_group.add_argument(
    "--rdmaccs", action="store_true", help="generate 166 bit RDKit/MACCS fingerprints")

parser.add_argument(
    "--aromaticity", metavar="NAME", choices=oe._aromaticity_flavor_names,
    default="openeye",
    help="use the named aromaticity model")

parser.add_argument(
    "--id-tag", metavar="NAME",
    help="tag name containing the record id (SD files only)")

parser.add_argument(
    "--in", metavar="FORMAT", dest="format",
    help="input structure format (default guesses from filename)")
parser.add_argument(
    "-o", "--output", metavar="FILENAME",
    help="save the fingerprints to FILENAME (default=stdout)")

parser.add_argument(
    "--errors", choices=["strict", "report", "ignore"], default="strict",
    help="how should structure parse errors be handled? (default=strict)")

parser.add_argument(
    "filenames", nargs="*", help="input structure files (default is stdin)")


#######

def main(args=None):
    args = parser.parse_args(args)

    cmdsupport.mutual_exclusion(parser, args, "path",
                                ("maccs166", "path", "substruct", "rdmaccs"))

    if args.maccs166:
        # Create the MACCS keys fingerprinter
        opener = types.get_fingerprint_family("OpenEye-MACCS166")()
    elif args.path:
        if not (16 <= args.numbits <= 65536):
            parser.error("--numbits must be between 16 and 65536 bits")

        if not (0 <= args.minbonds):
            parser.error("--minbonds must be 0 or greater")
        if not (args.minbonds <= args.maxbonds):
            parser.error("--maxbonds must not be smaller than --minbonds")

        opener = types.get_fingerprint_family("OpenEye-Path")(
            numbits = args.numbits,
            minbonds = args.minbonds,
            maxbonds = args.maxbonds,
            atype = args.atype,
            btype = args.btype)
    elif args.substruct:
        opener = types.get_fingerprint_family("ChemFP-Substruct-OpenEye")()
    elif args.rdmaccs:
        opener = types.get_fingerprint_family("RDMACCS-OpenEye")()
        
    else:
        parser.error("ERROR: fingerprint not specified?")

    if args.format is not None:
        if args.filenames:
            filename = args.filenames[0]
        else:
            filename = None
        if not oe.is_valid_format(filename, args.format):
            parser.error("Unsupported format specifier: %r" % (args.format,))

    if not oe.is_valid_aromaticity(args.aromaticity):
        parser.error("Unsupported aromaticity specifier: %r" % (args.aromaticity,))

    if not cmdsupport.is_valid_tag(args.id_tag):
        parser.error("Invalid id tag: %r" % (args.id_tag,))

    missing = cmdsupport.check_filenames(args.filenames)
    if missing:
        parser.error("Structure file %r does not exist" % (missing,))

    # Ready the input reader/iterator
    metadata, reader = cmdsupport.read_multifile_structure_fingerprints(
        opener, args.filenames, args.format, args.id_tag, args.aromaticity, args.errors)
    
    try:
        io.write_fps1_output(reader, args.output, metadata)
    except ParseError, err:
        sys.stderr.write("ERROR: %s. Exiting.\n" % (err,))
        raise SystemExit(1)
    
if __name__ == "__main__":
    main()
