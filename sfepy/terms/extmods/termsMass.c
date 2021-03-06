#include "termsVolume.h"
#include "terms.h"
#include "geommech.h"

#undef __FUNC__
#define __FUNC__ "dw_mass"
/*!
  @par Revision history:
  - 21.11.2006, c
*/
int32 dw_mass( FMField *out, FMField *coef, FMField *state,
	       FMField *bf, VolumeGeometry *vg,
               int32 isDiff )
{
  int32 ii, dim, nQP, nEP, ret = RET_OK;
  FMField *ftfu = 0, *ftf1 = 0, *ftf = 0;

  nQP = vg->bfGM->nLev;
  nEP = vg->bfGM->nCol;
  dim = vg->bfGM->nRow;

  if (isDiff) {
    fmf_createAlloc( &ftf, 1, nQP, nEP * dim, nEP * dim );
    fmf_createAlloc( &ftf1, 1, nQP, nEP, nEP );

    fmf_mulATB_nn( ftf1, bf, bf );

    for (ii = 0; ii < out->nCell; ii++) {
      FMF_SetCell( out, ii );
      FMF_SetCell( coef, ii );
      FMF_SetCell( vg->det, ii );

      bf_buildFTF( ftf, ftf1 );
      fmf_mul( ftf, coef->val );
      fmf_sumLevelsMulF( out, ftf, vg->det->val );

      ERR_CheckGo( ret );
    }
  } else {
    fmf_createAlloc( &ftfu, 1, nQP, dim * nEP, 1 );

    for (ii = 0; ii < out->nCell; ii++) {
      FMF_SetCell( out, ii );
      FMF_SetCell( state, ii );
      FMF_SetCell( coef, ii );
      FMF_SetCell( vg->det, ii );

      bf_actt( ftfu, bf, state );

      fmf_mul( ftfu, coef->val );
      fmf_sumLevelsMulF( out, ftfu, vg->det->val );

      ERR_CheckGo( ret );
    }
  }


 end_label:
  if (isDiff) {
    fmf_freeDestroy( &ftf1 );
    fmf_freeDestroy( &ftf );
  } else {
    fmf_freeDestroy( &ftfu );
  }

  return( ret );
}

#undef __FUNC__
#define __FUNC__ "dw_mass_scalar"
/*!
  @par Revision history:
  - 01.02.2008, c
*/
int32 dw_mass_scalar( FMField *out, FMField *coef,
		      FMField *state, FMField *bf, VolumeGeometry *vg,
		      int32 isDiff )
{
  int32 ii, dim, nQP, nEP, ret = RET_OK;
  FMField *ftfp = 0, *ftf = 0, *cftf = 0;

  nQP = vg->bfGM->nLev;
  nEP = vg->bfGM->nCol;
  dim = vg->bfGM->nRow;

  if (isDiff) {
    fmf_createAlloc( &ftf, 1, nQP, nEP, nEP );
    fmf_createAlloc( &cftf, 1, nQP, nEP, nEP );

    fmf_mulATB_nn( ftf, bf, bf );

    for (ii = 0; ii < out->nCell; ii++) {
      FMF_SetCell( out, ii );
      FMF_SetCell( vg->det, ii );
      if (coef->nCell > 1) {
	FMF_SetCell( coef, ii );
      }

      fmf_mulAF( cftf, ftf, coef->val );
      fmf_sumLevelsMulF( out, cftf, vg->det->val );

      ERR_CheckGo( ret );
    }
  } else {
    fmf_createAlloc( &ftfp, 1, nQP, nEP, 1 );

    for (ii = 0; ii < out->nCell; ii++) {
      FMF_SetCell( out, ii );
      FMF_SetCell( state, ii );
      FMF_SetCell( vg->det, ii );
      if (coef->nCell > 1) {
	FMF_SetCell( coef, ii );
      }

      bf_actt( ftfp, bf, state );
      fmf_mul( ftfp, coef->val );
      fmf_sumLevelsMulF( out, ftfp, vg->det->val );

      ERR_CheckGo( ret );
    }
  }

 end_label:
  if (isDiff) {
    fmf_freeDestroy( &ftf );
    fmf_freeDestroy( &cftf );
  } else {
    fmf_freeDestroy( &ftfp );
  }

  return( ret );
}

#undef __FUNC__
#define __FUNC__ "d_mass_scalar"
/*!
  @par Revision history:
  - 04.09.2007, c
*/
int32 d_mass_scalar( FMField *out, FMField *coef,
		     FMField *stateP, FMField *stateQ,
		     FMField *bf, VolumeGeometry *vg )
{
  int32 ii, dim, nQP, ret = RET_OK;
  FMField *qftfp = 0;

  nQP = vg->bfGM->nLev;
  dim = vg->bfGM->nRow;

  fmf_createAlloc( &qftfp, 1, nQP, 1, 1 );

  for (ii = 0; ii < out->nCell; ii++) {
    FMF_SetCell( out, ii );
    FMF_SetCell( stateP, ii );
    FMF_SetCell( stateQ, ii );
    FMF_SetCell( vg->det, ii );
    if (coef->nCell > 1) {
      FMF_SetCell( coef, ii );
    }
    fmf_mulATB_nn( qftfp, stateQ, stateP );
    fmf_mul( qftfp, coef->val );

    fmf_sumLevelsMulF( out, qftfp, vg->det->val );

    ERR_CheckGo( ret );
  }

 end_label:
  fmf_freeDestroy( &qftfp );

  return( ret );
}

#undef __FUNC__
#define __FUNC__ "dw_surf_mass_scalar"
/*!
  @par Revision history:
  - 09.03.2009, c
*/
int32 dw_surf_mass_scalar( FMField *out, FMField *coef,
			   FMField *state, FMField *bf, SurfaceGeometry *sg,
			   int32 isDiff )
{
  int32 ii, nFP, ret = RET_OK;
  FMField *ftfp = 0, *ftf = 0, *cftf = 0;

  nFP = bf->nCol;

  if (isDiff) {
    fmf_createAlloc( &ftf, 1, sg->nQP, nFP, nFP );
    fmf_createAlloc( &cftf, 1, sg->nQP, nFP, nFP );

    fmf_mulATB_nn( ftf, bf, bf );

    for (ii = 0; ii < out->nCell; ii++) {
      FMF_SetCell( out, ii );
      FMF_SetCell( sg->det, ii );
      if (coef->nCell > 1) {
	FMF_SetCell( coef, ii );
      }

      fmf_mulAF( cftf, ftf, coef->val );
      fmf_sumLevelsMulF( out, cftf, sg->det->val );

      ERR_CheckGo( ret );
    }
  } else {
    fmf_createAlloc( &ftfp, 1, sg->nQP, nFP, 1 );

    for (ii = 0; ii < out->nCell; ii++) {
      FMF_SetCell( out, ii );
      FMF_SetCell( sg->det, ii );
      if (coef->nCell > 1) {
	FMF_SetCell( coef, ii );
      }
      FMF_SetCell( state, ii );

      bf_actt( ftfp, bf, state );
      fmf_mulAF( ftfp, ftfp, coef->val );
      fmf_sumLevelsMulF( out, ftfp, sg->det->val );

      ERR_CheckGo( ret );
    }
  }

end_label:
  if (isDiff) {
    fmf_freeDestroy( &ftf );
    fmf_freeDestroy( &cftf );
  } else {
    fmf_freeDestroy( &ftfp );
  }

  return( ret );
}
