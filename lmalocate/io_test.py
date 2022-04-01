import raw_io

d = raw_io.RawLMA( '../../not_in_distro/example_data/LW_WestTexas_Llano_160908_012000.dat')

df = d.read_frame( 1 )