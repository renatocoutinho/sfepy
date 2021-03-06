/*!
  @par Revision history:
  - 21.11.2006, c
*/
#ifndef _TERMSMASS_H_
#define _TERMSMASS_H_

#include "common.h"
BEGIN_C_DECLS

#include "fmfield.h"
#include "geometry.h"

int32 dw_mass( FMField *out, FMField *coef, FMField *state,
	       FMField *bf, VolumeGeometry *vg,
               int32 isDiff );

int32 dw_mass_scalar( FMField *out, FMField *coef,
		      FMField *state, FMField *bf, VolumeGeometry *vg,
		      int32 isDiff );

int32 d_mass_scalar( FMField *out, FMField *coef,
		     FMField *stateP, FMField *stateQ,
		     FMField *bf, VolumeGeometry *vg );

int32 dw_surf_mass_scalar( FMField *out, FMField *coef,
			   FMField *state, FMField *bf, SurfaceGeometry *sg,
			   int32 isDiff );

END_C_DECLS

#endif /* Header */
