r"""
Dynamic Linear elasticity.

Find :math:`\ul{u}` such that:

.. math::
    \int_{\Omega} \rho\ \ul{v} \cdot \pdiff{\ul{u}}{t}
    + \int_{\Omega} D_{ijkl}\ e_{ij}(\ul{v}) e_{kl}(\ul{u})
    = 0
    \;, \quad \forall \ul{v} \;,

where

.. math::
    D_{ijkl} = \mu (\delta_{ik} \delta_{jl}+\delta_{il} \delta_{jk}) +
    \lambda \ \delta_{ij} \delta_{kl}
    \;.
"""
import numpy as nm
from linear_elastic import \
     filename_mesh, materials, regions, fields, ebcs, \
     integrals, solvers

options = {
    'ts' : 'ts',
    'save_steps' : -1,
}

variables = {
    'u' : ('unknown field', 'displacement', 0, 1),
    'v' : ('test field', 'displacement', 'u'),
}

# Put density to 'solid'.
materials['solid'][0].update({'rho' : 1000.0})

# Moving the PerturbedSurface region.
ebcs['PerturbedSurface'][1].update({'u.0' : 'ebc_sin'})

def ebc_sin(ts, coors, **kwargs):
    val = 0.01 * nm.sin(2.0*nm.pi*ts.nt)
    return nm.tile(val, (coors.shape[0],))

functions = {
    'ebc_sin' : (ebc_sin,),
}

equations = {
    'balance_of_forces in time' :
    """dw_mass_vector.i1.Omega( solid.rho, v, du/dt )
     + dw_lin_elastic_iso.i1.Omega( solid.lam, solid.mu, v, u ) = 0""",
}

solvers.update({
    'ts' : ('ts.simple',
            {'t0' : 0.0,
             't1' : 1.0,
             'dt' : None,
             'n_step' : 101
             }),
})

# Pre-assemble and factorize the matrix prior to time-stepping.
newton = solvers['newton']
newton[1].update({'problem' : 'linear'})

ls = solvers['ls']
ls[1].update({'presolve' : True})
