#!/usr/bin/env python2
# 12.01.2007, c 
import os.path as op
import shutil
from optparse import OptionParser

import numpy as nm
import numpy.linalg as nla
import scipy as sc

import sfepy
from sfepy.base.base import output, set_defaults, get_default, assert_
from sfepy.base.base import debug, Struct
from sfepy.base.conf import ProblemConf, get_standard_keywords
from sfepy.fem import ProblemDefinition
from sfepy.fem.evaluate import assemble_by_blocks
from sfepy.homogenization.phono import transform_plot_data, plot_logs, \
     plot_gaps, detect_band_gaps, compute_cat, compute_polarization_angles
from sfepy.homogenization.engine import HomogenizationEngine
from sfepy.applications import SimpleApp
from sfepy.solvers import Solver, eig
from sfepy.base.plotutils import plt

def make_save_hook( base_name, post_process_hook = None, file_per_var = None ):
    def save_phono_correctors( state, problem, ir, ic ):
        problem.save_state( (base_name % (ir, ic)) + '.vtk', state,
                            post_process_hook = post_process_hook,
                            file_per_var = file_per_var )
    return save_phono_correctors

def try_set_defaults( obj, attr, defaults ):
    try:
        values = getattr( obj, attr )
        set_defaults( values, defaults )
    except:
        values = defaults
    return values
    
def report_iw_cat( iw_dir, christoffel ):
    output( 'incident wave direction:' )
    output( iw_dir )
    output( 'Christoffel acoustic tensor:' )
    output( christoffel )

class AcousticBandGapsApp( SimpleApp ):

    def process_options( options ):
        """Application options setup. Sets default values for missing
        non-compulsory options."""
        get = options.get_default_attr
        
        clear_cache = get( 'clear_cache', {} )
        eigensolver = get( 'eigensolver', 'eig.sgscipy' )
        eig_problem = get( 'eig_problem', 'simple' )
        schur = get( 'schur', None )

        elasticity_contrast = get( 'elasticity_contrast', 1.0 )
        scale_epsilon = get( 'scale_epsilon', 1.0 )

        incident_wave_dir = get( 'incident_wave_dir', None )
        dispersion = get( 'dispersion', 'simple' )
        dispersion_conf = get( 'dispersion_conf', None )
        homogeneous = get( 'homogeneous', False )

        save = get( 'save_eig_vectors', (0, 0) )
        eig_range = get( 'eig_range', None )

        freq_margins = get( 'freq_margins', (5, 5) )
        # Given in per cent.
        freq_margins = 0.01 * nm.array( freq_margins, dtype = nm.float64 )

        fixed_eig_range = get( 'fixed_eig_range', None )

        # Given in per cent.
        freq_step = 0.01 * get( 'freq_step', 5 )

        feps = get( 'feps', 1e-8 )
        zeps = get( 'zeps', 1e-8 )
        teps = get( 'teps', 1e-4 )
        teps_rel = get( 'teps_rel', True )

        eig_vector_transform = get( 'eig_vector_transform', None )
        plot_transform = get( 'plot_transform', None )
        plot_transform_wave = get( 'plot_transform_wave', None )
        plot_transform_angle = get( 'plot_transform_angle', None )

        plot_options = get( 'plot_options', {'show' : True,'legend' : False,} )

        fig_name = get( 'fig_name', None )
        fig_name_wave = get( 'fig_name_wave', None )
        fig_name_angle = get( 'fig_name_angle', None )

        aux = {
            'resonance' : 'eigenfrequencies',
            'masked' : 'masked eigenfrequencies',
            'eig_min' : 'min eig($M^*$)',
            'eig_mid' : 'mid eig($M^*$)',
            'eig_max' : 'max eig($M^*$)',
            'y_axis' : 'eigenvalues of mass matrix $M^*$',
        }
        plot_labels = try_set_defaults( options, 'plot_labels', aux )

        aux = {
            'resonance' : 'eigenfrequencies',
            'masked' : 'masked eigenfrequencies',
            'eig_min' : r'$\kappa$(min)',
            'eig_mid' : r'$\kappa$(mid)',
            'eig_max' : r'$\kappa$(max)',
            'y_axis' : 'polarization angles',
        }
        plot_labels_angle = try_set_defaults( options, 'plot_labels_angle', aux )

        aux = {
            'resonance' : 'eigenfrequencies',
            'masked' : 'masked eigenfrequencies',
            'eig_min' : r'wave number (min)',
            'eig_mid' : r'wave number (mid)',
            'eig_max' : r'wave number (max)',
            'y_axis' : 'wave numbers',
        }
        plot_labels_wave = try_set_defaults( options, 'plot_labels_wave', aux )

        plot_rsc =  {
            'resonance' : {'linewidth' : 0.5, 'color' : 'r', 'linestyle' : '-' },
            'masked' : {'linewidth' : 0.5, 'color' : 'r', 'linestyle' : ':' },
            'x_axis' : {'linewidth' : 0.5, 'color' : 'k', 'linestyle' : '--' },
            'eig_min' : {'linewidth' : 0.5, 'color' : 'b', 'linestyle' : '--' },
            'eig_mid' : {'linewidth' : 0.5, 'color' : 'b', 'linestyle' : '-.' },
            'eig_max' : {'linewidth' : 0.5, 'color' : 'b', 'linestyle' : '-' },
            'strong_gap' : {'linewidth' : 0, 'facecolor' : (1, 1, 0.5) },
            'weak_gap' : {'linewidth' : 0, 'facecolor' : (1, 1, 1) },
            'propagation' : {'linewidth' : 0, 'facecolor' : (0.5, 1, 0.5) },
            'params' : {'axes.labelsize': 'large',
                        'text.fontsize': 'large',
                        'legend.fontsize': 'large',
                        'xtick.labelsize': 'large',
                        'ytick.labelsize': 'large',
                        'text.usetex': False},
        }
        plot_rsc = try_set_defaults( options, 'plot_rsc', plot_rsc )

        eigenmomentum = get( 'eigenmomentum', None,
                             'missing "eigenmomentum" in options!' )
        
        region_to_material = get( 'region_to_material', None,
                                  'missing "region_to_material" in options!' )

        tensor_names = get( 'tensor_names', None,
                            'missing "tensor_names" in options!' )

        volume = get( 'volume', None, 'missing "volume" in options!' )

        if eig_problem == 'simple_liquid':
            liquid_region = get('liquid_region', None,
                                'missing "liquid_region" in options!')
        else:
            liquid_region = None

        return Struct( **locals() )
    process_options = staticmethod( process_options )

    def process_options_pv( options ):
        """Application options setup for phase velocity computation. Sets
        default values for missing non-compulsory options."""
        get = options.get_default_attr

        clear_cache = get( 'clear_cache', {} )
        eigensolver = get( 'eigensolver', 'eig.sgscipy' )

        incident_wave_dir = get( 'incident_wave_dir', None )
        dispersion = get( 'dispersion', 'simple' )
        dispersion_conf = get( 'dispersion_conf', None )
        homogeneous = get( 'homogeneous', False )
        fig_suffix = get( 'fig_suffix', '.pdf' )

        region_to_material = get( 'region_to_material', None,
                                  'missing "region_to_material" in options!' )

        tensor_names = get( 'tensor_names', None,
                            'missing "tensor_names" in options!' )

        volume = get( 'volume', None, 'missing "volume" in options!' )

        return Struct( **locals() )
    process_options_pv = staticmethod( process_options_pv )

    def __init__( self, conf, options, output_prefix, **kwargs ):
        SimpleApp.__init__( self, conf, options, output_prefix,
                            init_equations = False )

        self.setup_options()
        self.cached_coefs = None
        self.cached_iw_dir = None
        self.cached_christoffel = None
        self.cached_evp = None

        output_dir = self.problem.output_dir
        shutil.copyfile( conf._filename,
                         op.join( output_dir, op.basename( conf._filename ) ) )

    def setup_options( self ):
        SimpleApp.setup_options( self )
        
        if self.options.phase_velocity:
            process_options = AcousticBandGapsApp.process_options_pv
        else:
            process_options = AcousticBandGapsApp.process_options
        self.app_options += process_options( self.conf.options )
    
    def call( self ):
        """In parametric runs, cached data (homogenized coefficients,
        Christoffel acoustic tensor and eigenvalue problem solution) are
        cleared according to 'clear_cache' aplication options.

        Example:

        clear_cache = {'cached_christoffel' : True, 'cached_evp' : True}
        """
        options = self.options

        for key, val in self.app_options.clear_cache.iteritems():
            if val and key.startswith('cached_'):
                setattr(self, key, None)

        if options.phase_velocity:
            # No band gaps in this case.
            return self.compute_phase_velocity()

        evp = self.solve_eigen_problem()

        self.fix_eig_range( evp.eigs.shape[0] )

        if options.detect_band_gaps:
            bg = detect_band_gaps( self.problem, evp.kind,
                                   evp.eigs_rescaled, evp.eig_vectors,
                                   self.app_options, self.conf.funmod )

            if options.plot:
                plot_range, teigs = transform_plot_data( bg.logs.eigs,
                                                         bg.opts.plot_transform,
                                                         self.conf.funmod )

                plot_rsc = bg.opts.plot_rsc
                plot_opts =  bg.opts.plot_options
                plot_labels =  bg.opts.plot_labels
                
                plt.rcParams.update( plot_rsc['params'] )

                fig = plot_gaps( 1, plot_rsc, bg.gaps, bg.kinds,
                                 bg.freq_range_margins, plot_range,
                                 clear = True )
                fig = plot_logs( 1, plot_rsc, plot_labels, bg.logs.freqs, teigs,
                                 bg.valid[bg.eig_range],
                                 bg.freq_range_initial,
                                 plot_range, False,
                                 show_legend = plot_opts['legend'],
                                 new_axes = True )

                fig_name = bg.opts.fig_name
                if fig_name is not None:
                    fig.savefig( fig_name )
                if plot_opts['show']:
                    plt.show()

        elif options.analyze_dispersion:
            christoffel, iw_dir = self.compute_cat(ret_iw_dir=True)

            bg = detect_band_gaps( self.problem, evp.kind,
                                   evp.eigs_rescaled, evp.eig_vectors,
                                   self.app_options, self.conf.funmod,
                                   christoffel = christoffel )

            output( 'computing polarization angles...' )
            pas = compute_polarization_angles( iw_dir, bg.logs.eig_vectors )
            output( '...done' )

            bg.polarization_angles = pas

            output( 'computing phase velocity...' )
            bg.phase_velocity = self.compute_phase_velocity()
            output( '...done' )

            if options.plot:
                plot_rsc = bg.opts.plot_rsc
                plot_opts =  bg.opts.plot_options
                plt.rcParams.update( plot_rsc['params'] )

                aux = transform_plot_data( pas,
                                           bg.opts.plot_transform_angle,
                                           self.conf.funmod )
                plot_range, pas = aux
                
                plot_labels =  bg.opts.plot_labels_angle

                fig = plot_gaps( 1, plot_rsc, bg.gaps, bg.kinds,
                                 bg.freq_range_margins, plot_range,
                                 clear = True )
                fig = plot_logs( 1, plot_rsc, plot_labels, bg.logs.freqs, pas,
                                 bg.valid[bg.eig_range],
                                 bg.freq_range_initial,
                                 plot_range, False,
                                 show_legend = plot_opts['legend'],
                                 new_axes = True )

                fig_name = bg.opts.fig_name_angle
                if fig_name is not None:
                    fig.savefig( fig_name )

                aux = transform_plot_data( bg.logs.eigs,
                                           bg.opts.plot_transform_wave,
                                           self.conf.funmod )
                plot_range, teigs = aux

                plot_labels =  bg.opts.plot_labels_wave

                fig = plot_gaps( 2, plot_rsc, bg.gaps, bg.kinds,
                                 bg.freq_range_margins, plot_range,
                                 clear = True )
                fig = plot_logs( 2, plot_rsc, plot_labels, bg.logs.freqs, teigs,
                                 bg.valid[bg.eig_range],
                                 bg.freq_range_initial,
                                 plot_range, False,
                                 show_legend = plot_opts['legend'],
                                 new_axes = True )

                fig_name = bg.opts.fig_name_wave
                if fig_name is not None:
                    fig.savefig( fig_name )
                if plot_opts['show']:
                    plt.show()

        else:
            bg = None

        return evp, bg

    def fix_eig_range( self, n_eigs ):
        eig_range = get_default( self.app_options.eig_range, (0, n_eigs) )
        if eig_range[-1] < 0:
            eig_range[-1] += n_eigs + 1

        assert_( eig_range[0] < (eig_range[1] - 1) )
        assert_( eig_range[1] <= n_eigs )
        self.app_options.eig_range = eig_range
    
    def solve_eigen_problem( self, ofn_trunk = None, post_process_hook = None ):

        if self.cached_evp is not None:
            return self.cached_evp

        problem = self.problem
        ofn_trunk = get_default( ofn_trunk, problem.ofn_trunk,
                                 'output file name trunk missing!' )
        post_process_hook = get_default( post_process_hook,
                                         self.post_process_hook )
 
        conf = self.conf
        
        eig_problem = self.app_options.eig_problem
        if eig_problem in ['simple', 'simple_liquid']:
            problem.set_equations( conf.equations )
            problem.time_update()
            problem.update_materials()

            mtx_a = problem.evaluate(conf.equations['lhs'], mode='weak',
                                     auto_init=True, dw_mode='matrix')

            mtx_m = problem.evaluate(conf.equations['rhs'], mode='weak',
                                     dw_mode='matrix')

        elif eig_problem == 'schur':
            # A = K + B^T D^{-1} B.
            mtx = assemble_by_blocks( conf.equations, self.problem,
                                      ebcs = conf.ebcs,
                                      epbcs = conf.epbcs )
            problem.set_equations( conf.equations )
            problem.time_update()
            problem.update_materials()

            ls = Solver.any_from_conf( problem.ls_conf,
                                       presolve = True, mtx = mtx['D'] )

            mtx_b, mtx_m = mtx['B'], mtx['M']
            mtx_dib = nm.empty( mtx_b.shape, dtype = mtx_b.dtype )
            for ic in xrange( mtx_b.shape[1] ):
                mtx_dib[:,ic] = ls( mtx_b[:,ic].toarray().squeeze() )
            mtx_a = mtx['K'] + mtx_b.T * mtx_dib

        else:
            raise NotImplementedError

##     from sfepy.base.plotutils import spy, plt
##     spy( mtx_b, eps = 1e-12 )
##     plt.show()
##     mtx_a.save( 'a.txt', format='%d %d %.12f\n' )
##     mtx_b.save( 'b.txt', format='%d %d %.12f\n' )
##     pause()

        output( 'computing resonance frequencies...' )
        tt = [0]

        if isinstance( mtx_a, sc.sparse.spmatrix ):
            mtx_a = mtx_a.toarray()
        if isinstance( mtx_m, sc.sparse.spmatrix ):
            mtx_m = mtx_m.toarray()

        eigs, mtx_s_phi = eig(mtx_a, mtx_m, return_time=tt,
                              method=self.app_options.eigensolver)
        eigs[eigs<0.0] = 0.0
        output( '...done in %.2f s' % tt[0] )
        output( 'original eigenfrequencies:' )        
        output( eigs )
        opts = self.app_options
        epsilon2 = opts.scale_epsilon * opts.scale_epsilon
        eigs_rescaled = (opts.elasticity_contrast / epsilon2)  * eigs
        output( 'rescaled eigenfrequencies:' )        
        output( eigs_rescaled )
        output( 'number of eigenfrequencies: %d' % eigs.shape[0] )

        try:
            assert_( nm.isfinite( eigs ).all() )
        except ValueError:
            debug()

        # B-orthogonality check.
##         print nm.dot( mtx_s_phi[:,5], nm.dot( mtx_m, mtx_s_phi[:,5] ) )
##         print nm.dot( mtx_s_phi[:,5], nm.dot( mtx_m, mtx_s_phi[:,0] ) )
##         debug()

        n_eigs = eigs.shape[0]

        variables = problem.get_variables()

        mtx_phi = nm.empty( (variables.di.ptr[-1], mtx_s_phi.shape[1]),
                           dtype = nm.float64 )

        make_full = variables.make_full_vec
        if eig_problem in ['simple', 'simple_liquid']:
            for ii in xrange( n_eigs ):
                mtx_phi[:,ii] = make_full( mtx_s_phi[:,ii] )
            eig_vectors = mtx_phi
            
        elif eig_problem == 'schur':
            # Update also eliminated variables.
            schur = self.app_options.schur
            primary_var = schur['primary_var']
            eliminated_var = schur['eliminated_var']

            mtx_s_phi_schur = - sc.dot( mtx_dib, mtx_s_phi )
            aux = nm.empty( (variables.adi.ptr[-1],),
                            dtype = nm.float64 )
            set = variables.set_state_part
            for ii in xrange( n_eigs ):
                set( aux, mtx_s_phi[:,ii], primary_var, stripped = True )
                set( aux, mtx_s_phi_schur[:,ii], eliminated_var,
                     stripped = True )

                mtx_phi[:,ii] = make_full( aux )

            indx = variables.get_indx( primary_var )
            eig_vectors = mtx_phi[indx,:]

        save = self.app_options.save
        out = {}
        state = problem.create_state()
        for ii in xrange( n_eigs ):
            if (ii >= save[0]) and (ii < (n_eigs - save[1])): continue
            state.set_full(mtx_phi[:,ii], force=True)
            aux = state.create_output_dict()
            for name, val in aux.iteritems():
                out[name+'%03d' % ii] = val

        if post_process_hook is not None:
            out = post_process_hook( out, problem, mtx_phi )

        problem.domain.mesh.write( ofn_trunk + '.vtk', io = 'auto', out = out )

        fd = open( ofn_trunk + '_eigs.txt', 'w' )
        eigs.tofile( fd, ' ' )
        fd.close()

        evp = Struct( kind = eig_problem,
                      eigs = eigs, eigs_rescaled = eigs_rescaled,
                      eig_vectors = eig_vectors )
        self.cached_evp = evp

        return evp

    def eval_homogenized_coefs( self ):
        if self.cached_coefs is not None:
            return self.cached_coefs

        opts = self.app_options

        if opts.homogeneous:
            rtm = opts.region_to_material
            mat_region = rtm.keys()[0]
            mat_name = rtm[mat_region]
            
            self.problem.update_materials()

            mat = self.problem.materials[mat_name]
            coefs = mat.get_data( mat_region, 0, opts.tensor_names )
            
        else:
            dc = opts.dispersion_conf
            dconf = ProblemConf.from_dict( dc['input'], dc['module'] )

            dconf.materials = self.conf.materials
            dconf.regions.update( self.conf.regions )
            dconf.options['output_dir'] = self.problem.output_dir

            volume = opts.volume(self.problem, 'Y')
            problem = ProblemDefinition.from_conf(dconf, init_equations=False)
            he = HomogenizationEngine( problem, self.options, volume = volume )
            coefs = he()

##         print coefs
##         pause()
        output.prefix = self.output_prefix

        self.cached_coefs = coefs
        
        return coefs

    def compute_cat( self, ret_iw_dir=False ):
        """Compute the Christoffel acoustic tensor, given the incident wave
        direction."""
        opts = self.app_options
        iw_dir = nm.array( opts.incident_wave_dir, dtype = nm.float64 )

        dim = self.problem.get_dim()
        assert_( dim == iw_dir.shape[0] )

        iw_dir = iw_dir / nla.norm( iw_dir )

        if self.cached_christoffel is not None:
            christoffel = self.cached_christoffel

        else:
            coefs = self.eval_homogenized_coefs()
            christoffel = compute_cat( coefs, iw_dir,
                                       self.app_options.dispersion )
            report_iw_cat( iw_dir, christoffel )

            self.cached_christoffel = christoffel

        if ret_iw_dir:
            return christoffel, iw_dir

        else:
            return christoffel

    def compute_phase_velocity( self ):
        from sfepy.homogenization.phono import compute_density_volume_info
        opts = self.app_options
        dim = self.problem.domain.mesh.dim

        christoffel = self.compute_cat()

        self.problem.update_materials()
        dv_info = compute_density_volume_info( self.problem, opts.volume,
                                               opts.region_to_material )
        output( 'average density:', dv_info.average_density )

        eye = nm.eye( dim, dim, dtype = nm.float64 )
        mtx_mass = eye * dv_info.average_density

        meigs, mvecs = eig( mtx_mass, mtx_b = christoffel,
                            eigenvectors = True, method = opts.eigensolver )
        phase_velocity = 1.0 / nm.sqrt( meigs )

        return phase_velocity
    
usage = """%prog [options] filename_in"""

help = {
    'filename' :
    'basename of output file(s) [default: <basename of input file>]',
    'detect_band_gaps' :
    'detect frequency band gaps',
    'analyze_dispersion' :
    'analyze dispersion properties (low frequency domain)',
    'plot' :
    'plot frequency band gaps, assumes -b',
    'phase_velocity' :
    'compute phase velocity (frequency-independet mass only)'
}

def main():
    parser = OptionParser(usage = usage, version = "%prog " + sfepy.__version__)
    parser.add_option( "-o", "", metavar = 'filename',
                       action = "store", dest = "output_filename_trunk",
                       default = None, help = help['filename'] )
    parser.add_option( "-b", "--band-gaps",
                       action = "store_true", dest = "detect_band_gaps",
                       default = False, help = help['detect_band_gaps'] )
    parser.add_option( "-d", "--dispersion",
                       action = "store_true", dest = "analyze_dispersion",
                       default = False, help = help['analyze_dispersion'] )
    parser.add_option( "-p", "--plot",
                       action = "store_true", dest = "plot",
                       default = False, help = help['plot'] )
    parser.add_option( "--phase-velocity",
                       action = "store_true", dest = "phase_velocity",
                       default = False, help = help['phase_velocity'] )

    options, args = parser.parse_args()
    if options.plot:
        if plt is None:
            output( 'matplotlib.pyplot cannot be imported, ignoring option -p!' )
            options.plot = False
        elif options.analyze_dispersion == False:
            options.detect_band_gaps = True

    if (len( args ) == 1):
        filename_in = args[0];
    else:
        parser.print_help(),
        return

    required, other = get_standard_keywords()
    required.remove( 'solver_[0-9]+|solvers' )
    if options.phase_velocity:
        required.remove( 'ebc_[0-9]+|ebcs' )
        required.remove( 'equations' )
    conf = ProblemConf.from_file( filename_in, required, other )

    app = AcousticBandGapsApp( conf, options, 'eigen:' )
    opts = conf.options
    if hasattr( opts, 'parametric_hook' ): # Parametric study.
        parametric_hook = conf.get_function(opts.parametric_hook)
        app.parametrize( parametric_hook )
    app()

if __name__ == '__main__':
##     mtx_k = io.read_sparse_matrix_hdf5( '1todo/K.h5', output_format = 'csr' )
##     print mtx_k.__repr__()
##     mtx_m = io.read_sparse_matrix_hdf5( '1todo/M.h5', output_format = 'csr' )
##     print mtx_m.__repr__()
##     mtx_k.save( 'k.txt', format='%d %d %.12f\n' )
##     mtx_m.save( 'm.txt', format='%d %d %.12f\n' )
##     eigs, mtx_s_phi = eig( mtx_k.toarray(), mtx_m.toarray(),
##                          print_time = True )
##     print eigs
##     eigs, aux = eig( mtx_m.toarray(),
##                      print_time = True )
##     print eigs
##     pause()
    main()
