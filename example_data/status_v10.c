#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SYNC 0xaa55

void parse_hk(short *status, int *hk_parse);
int get_status(FILE *in, short *status);
int get_next(FILE *in, int max_data_len, unsigned short *data, unsigned short *status);
int check_data_v10(unsigned short *data, int data_len);
int check_data_v11(unsigned short *data, int data_len);

main(int argc, char *argv[])
{
	FILE *in,*out,*hk;
	char filename[80],fout[80],fhk[80];
	short status[9];
	int hk_parse[21];
	int trig_count;
	int i;

	unsigned short *data;
	int data_len,max_data_len;
	int count,last_count=-1;

	int phase;

	float lat,lng,alt;
	int max_data,max_max_data=0;

	unsigned short data_parse[11],sec,min,hour,month,day,year,
	               ver,thresh,id;

	if (argc != 2)
	{
		fprintf(stderr,"Usage:  %s file_name\n",argv[0]);
		exit(0);
	}
	strcpy(filename,argv[1]);
	if ((in = fopen(filename,"r")) == NULL)
	{
		fprintf(stderr,"%s:  Cannot find file %s\n ",argv[0],filename);
		exit(0);
	}

	// Find the first status word in the file
	if ((count = get_status(in,status)) == -1)
	{
		fprintf(stderr,"No status word found in file %s\n",filename);
		exit(0);
	}
	parse_hk(&status[0],&hk_parse[0]);
	year = hk_parse[0]+2000;
	month = hk_parse[1];
	day = hk_parse[2];
	hour = hk_parse[3];
	min = hk_parse[4];
	sec = hk_parse[5];
	ver = hk_parse[6];
	thresh = hk_parse[7];
	phase = hk_parse[8];
	id = hk_parse[20]+'A'-1;
	printf("%c %4d/%02d/%02d %02d:%02d:%02d v%2d 0x%02x %4d\n",
			id,year,month,day,hour,min,sec,ver,thresh,phase);
	if (ver == 10)  max_data_len = 12500*3;
	else max_data_len = 100000*3; 
	data = (unsigned short *) malloc(max_data_len + 9);
	for (;;) {
		data_len = get_next(in,max_data_len,data,status);
		if (data_len == -1) {
			printf("End of file reached\n");
			fprintf(stderr,"max_max_data = %3d\n",max_max_data);
			exit(0);
		}
		if (data_len % 3 != 0) printf("Error in file:  data blocks not mod 3\n");
		for (i=0,max_data=0;i<data_len;i+=3) {
			if ((data[i+2]&0x00ff) > max_data) max_data = data[i+2]&0x00ff;
		}
		if (max_data > max_max_data) max_max_data = max_data;
//		printf("data_len = %4d\n",data_len);
		parse_hk(&status[0],&hk_parse[0]);
		year = hk_parse[0]+2000;
		month = hk_parse[1];
		day = hk_parse[2];
		hour = hk_parse[3];
		min = hk_parse[4];
		sec = hk_parse[5];
		ver = hk_parse[6];
		thresh = hk_parse[7];
		phase = hk_parse[8];
		trig_count = hk_parse[9];
		id = hk_parse[20]+'A'-1;
		if (trig_count != data_len/3) {
			printf("Error in file:  wrong number of triggers between status blocks\n");
			printf("                Should have %d triggers, file has only %d\n",trig_count,data_len/3);
		}
		if (ver == 10) check_data_v10(data,data_len);
		else check_data_v11(data,data_len);
		printf("%c %4d/%02d/%02d %02d:%02d:%02d v%2d 0x%02x %4d %6d %3d",
			id,year,month,day,hour,min,sec,ver,thresh,phase,trig_count,max_data);
		if (sec % 12 == 11) {
			lat = hk_parse[10]*90.0/324000000.0;
			lng = hk_parse[11]*180.0/648000000.0;
			alt = hk_parse[12]/100.0;
			printf(" %2d", hk_parse[16]);
			if ((hk_parse[17] & 0xe000) == 0x8000) printf(" ph");
			else printf(" pf");
			printf(" %2d", hk_parse[18]);
			printf(" %12.8f", lat);
			printf(" %13.8f", lng);
			printf(" %i", hk_parse[11]);
			printf(" %7.2f", alt);
		}
		printf("\n");
	}
}

void parse_hk(short *data, int *hk_parse)
{
	static int rh, temp, sat_vis,sat_track, sat_stat;
	int temp1,temp2,gps_info,i;
	static int lat43,lat21,lng43,lng21,alt43,alt21,vel43,vel21,hdg;

	for (i=0;i<20;i++) hk_parse[i] = 0;
	hk_parse[0]=(data[0])&0x7f; // Year
	hk_parse[1]=(data[3])&0x0f; // Month
	hk_parse[2]=(data[3]>>4)&0x1f; // Day
	hk_parse[3]=(data[3]>>9)&0x1f; // Hour
	hk_parse[4]=(data[2]&0x3f); // Minute
	hk_parse[5]=((data[2]>>6)&0x3f); // Second

	hk_parse[6] = (data[0] >> 7) & 0x3f;  // Version
	hk_parse[7] = data[1] & 0xff;  // Threshold
	hk_parse[8] = data[6] & 0x7fff;  // PC
	if (!(data[1] & 0x4000)) hk_parse[8] *= -1;
	temp2 = data[1] & 0x0c00;
	temp2 = temp2 << 5;
	temp1 = data[4] & 0x7fff;
	hk_parse[9] = temp2 | temp1;  // Trig count
	temp2 = data[1] & 0x1000;
	temp2 = temp2 >> 5;
	temp1 = (data[5]>>8) & 0x007f;
	hk_parse[20] = temp2 | temp1;
	temp2 = data[1] & 0x2000;
	temp2 = temp2 << 2;
	temp1 = data[7] & 0x7fff;
	gps_info = temp2 | temp1;
	switch (hk_parse[5] % 12) {
		case 0:
			lat43 = gps_info & 0xffff;
			break;
		case 1:
			lat21 = gps_info & 0xffff;
			break;
		case 2:
			lng43 = gps_info & 0xffff;
			break;
		case 3:
			lng21 = gps_info & 0xffff;
			break;
		case 4:
			alt43 = gps_info & 0xffff;
			break;
		case 5:
			alt21 = gps_info & 0xffff;
			break;
		case 6:
			vel43 = gps_info & 0xffff;
			break;
		case 7:
			vel21 = gps_info & 0xffff;
			break;
		case 8:
			hdg = gps_info;
			break;
		case 9:
			sat_vis = (gps_info >> 8)&0xff;
			sat_track = gps_info&0xff;
			break;
		case 10:
			sat_stat = gps_info & 0xffff;
			break;
		case 11:
			temp = (gps_info >> 8) - 40;
			hk_parse[10]=(lat43 << 16) | lat21;
			hk_parse[11]=(lng43 << 16) | lng21;
			hk_parse[12]=(alt43 << 16) | alt21;
			hk_parse[13]=(vel43 << 16) | vel21;
			hk_parse[14]=hdg;
			hk_parse[15] = sat_vis;
			hk_parse[16] = sat_track;
			hk_parse[17] = sat_stat;
			hk_parse[18] = temp;
			hk_parse[19] = rh;
			break;
	}
}

int get_status(FILE *in, short *status)
{
	int i, j;
	static int count=0;

	unsigned short stat[9];

	for (i=0;i<8;i++)
		fread(&stat[i],sizeof(short),1,in);
	j = (i+1) % 9;
	while (!feof(in))
	{
		fread(&stat[i],sizeof(short),1,in);
		count++;
		if ((stat[i] == SYNC) && ((stat[j]&0xbf00) == 0x8500)) break;
		i = ++i % 9;
		j = (i+1) % 9;
	}
	if (feof(in)) return(-1);
	for (j=0;j<9;j++) {
		i = ++i % 9;
		status[j] = stat[i];
	}
	return(count-8);
}

int get_next(FILE *in, int max_data_len, unsigned short *data, unsigned short *status)
{
	int i,j,k;

	for (i=0;i < 8; i++) fread(&data[i],sizeof(short),1,in);
	j = 0;
	for (;i < max_data_len + 9; i++,j++) {
		fread(&data[i],sizeof(short),1,in);
		if (feof(in)) return(-1);
		if ((data[i] == SYNC) && ((data[j]&0xbf00) == 0x8500)) {
			for (k=0;k<9;k++,j++ ) {
				status[k] = data[j];
			}
			return(i-8);
		}
	}
	fprintf(stderr,"Error in data file: too many data blocks between status blocks\n");
	exit(-1);
}

/*
 * Check data for consistency.  Look for pos-neg-pos, and look for 
 * monotonicity in time.  Return after first error
 */
int check_data_v10(unsigned short *data, int data_len)
{
	int i; int micro, micro_last;

	micro_last = -1;
	for (i=0;i<data_len;i+=3) {
		if (data[i] & 0x8000) {
			printf("Error in data file:  Not pos-neg-pos\n");
			return(-1);
		}
		if ((data[i+1] & 0xc000)!=0xc000) {
			printf("Error in data file:  Not pos-neg-pos\n");
			return(-1);
		}
		if (data[i+2] & 0x8000) {
			printf("Error in data file:  Not pos-neg-pos\n");
			return(-1);
		}
		micro = data[i+1] & 0x3fff;
		if (micro <= micro_last) {
			printf("Monotonicity error in data file\n");
			return(-1);
		}
		micro_last = micro;
	}
}

int check_data_v11(unsigned short *data, int data_len)
{
	int i; int micro, micro_last,m1,m2;

	micro_last = -1;
	for (i=0;i<data_len;i+=3) {
		if (data[i] & 0x8000) {
			printf("Error in data file:  Not pos-neg-pos\n");
			return(-1);
		}
		if ((data[i+1] & 0xc000) != 0xc000) {
			printf("Error in data file:  Not pos-neg-pos\n");
			return(-1);
		}
		if (data[i+2] & 0x8000) {
			printf("Error in data file:  Not pos-neg-pos\n");
			return(-1);
		}
		m1 = data[i+1] & 0x3fff;
		m2 = (data[i]&0x0700)>>8;
		micro = m1 | (m2 << 14);
		if (micro <= micro_last) {
			printf("Monotonicity error in data file\n");
			return(-1);
		}
		micro_last = micro;
	}
}

