import copy

import numpy as np
from scipy.stats import lognorm

SPEED_OF_SOUND_IN_WATER = 1442.5  # m/s


class SedimentSizeDistribution:

    def __init__(self, particle_diameters, cumulative_volume_distribution):
        """
        
        :param particle_diameters: 
        :param cumulative_volume_distribution: 
        """

        self._cdf_diameters = copy.deepcopy(particle_diameters)
        self._volume_cdf = copy.deepcopy(cumulative_volume_distribution)

        self._number_cdf = self._calc_number_cdf(self._cdf_diameters, self._volume_cdf)

        self._pdf_diameters, self._number_pdf = self._calc_number_pdf(self._cdf_diameters, self._volume_cdf)
        _, self._volume_pdf = self._calc_volume_pdf(self._cdf_diameters, self._volume_cdf)

    @staticmethod
    def _calc_number_cdf(cum_particle_diameters, volume_cdf):
        """

        :param cum_particle_diameters: Diameters of the cumulative density function
        :param volume_cdf:
        :return: 
        """

        diameter_diff = np.diff(cum_particle_diameters)
        diameter_mid_points = cum_particle_diameters[:-1] + diameter_diff / 2

        particle_volumes = 4 / 3 * np.pi * (diameter_mid_points / 2) ** 3

        volume_fractions = np.diff(volume_cdf)
        number_fractions = volume_fractions / particle_volumes / np.sum(volume_fractions / particle_volumes)

        cumulative_number_distribution = np.repeat(np.nan, volume_cdf.shape)

        cumulative_number_distribution[0] = 1 - np.sum(number_fractions)
        cumulative_number_distribution[1:] = np.cumsum(number_fractions) + cumulative_number_distribution[0]

        return cumulative_number_distribution

    @staticmethod
    def _calc_number_pdf(diameters, volume_cdf):
        """Calculates the probability density function of the size distribution by number of particles.
        
        Moore et al. 2013
        
        :param diameters: 
        :param volume_cdf: 
        :return: 
        """

        volume_fractions = np.diff(volume_cdf)

        diameters_diff = np.diff(diameters)
        distribution_diameters = diameters[:-1] + diameters_diff/2
        particle_volumes = 4/3*np.pi*(distribution_diameters/2)**3

        number_in_bins = volume_fractions/particle_volumes

        number_fractions = number_in_bins/np.sum(number_in_bins)

        number_distribution = number_fractions/diameters_diff

        return distribution_diameters, number_distribution

    @staticmethod
    def _calc_volume_pdf(diameters, cumulative_volume_distribution):
        """Calculates the probability density function of the size distribution by volume of particles.
        
        :param diameters: 
        :param cumulative_volume_distribution: 
        :return: 
        """

        volume_fractions = np.diff(cumulative_volume_distribution)

        diameters_diff = np.diff(diameters)
        distribution_diameters = diameters[:-1] + diameters_diff/2

        volume_pdf = volume_fractions/diameters_diff

        return distribution_diameters, volume_pdf

    def calc_form_function(self, frequency):
        """
        
        :param frequency: Frequency of acoustic signal, in kilohertz
        :return: 
        """

        # wavelength in meters
        wavelength = SPEED_OF_SOUND_IN_WATER/(frequency*1000)

        wave_number = 2*np.pi/wavelength

        dimensionless_wave_numbers = wave_number*(self._pdf_diameters / 2 / 1000)

        form_function = self.form_function(dimensionless_wave_numbers)

        mean_form_function = self.mean_form_function(self._pdf_diameters, self._number_cdf, form_function)

        return mean_form_function

    @staticmethod
    def form_function(x):
        """Returns a backscatter form function for a single particle size as calculated with equation 6 of 
        Throne and Meral (2008)

        :param x:    Dimensionless wave number, x = ka, where k is the acoustic wave number and a is the particle radius 
        of the suspended sediment.

        :return: f_e
        """

        # first bracketed term
        a = 1 - 0.35 * np.exp(-((x - 1.5) / 0.7) ** 2)

        # second bracketed term
        b = 1 + 0.5 * np.exp(-((x - 1.8) / 2.2) ** 2)

        dividend = x ** 2 * a * b
        divisor = 1 + 0.9 * x ** 2

        f_e = dividend / divisor

        return f_e

    def get_mean_diameter(self, distribution='volume'):
        """Returns the mean particle diameter of the distribution based on the volume distribution.
        
        :param distribution:
        :return: mean_diameter 
        """

        if distribution == 'volume':

            mean_diameter = np.trapz(self._pdf_diameters * self._volume_pdf, self._pdf_diameters)

        elif distribution == 'number':

            mean_diameter = np.trapz(self._pdf_diameters * self._volume_cdf,
                                     self._pdf_diameters)

        else:

            mean_diameter = None

        return mean_diameter

    def get_median_diameter(self, distribution='volume'):
        """Returns the median particle diameter of the distribution based on the volume distribution.
        
        :return: 
        """

        if distribution == 'volume':

            median_diameter = np.interp(0.5, self._volume_cdf, self._cdf_diameters)

        elif distribution == 'number':

            median_diameter = np.interp(0.5, self._number_cdf, self._cdf_diameters)

        else:

            median_diameter = None

        return median_diameter

    def get_number_cdf(self):
        """
        
        :return: 
        """

        return self._cdf_diameters.copy(), self._number_cdf.copy()

    def get_number_pdf(self):
        """
        
        :return: diameters, number_distribution
        """

        return self._pdf_diameters.copy(), self._number_pdf.copy()

    def get_volume_cdf(self):
        """
        
        :return: 
        """

        return self._cdf_diameters.copy(), self._volume_cdf.copy()

    def get_volume_pdf(self):
        """
        
        :return: diameters, volume_distribution
        """

        return self._pdf_diameters.copy(), self._volume_pdf.copy()

    @staticmethod
    def mean_form_function(a, prob_dist, f_e):
        """Returns form factor for a distribution of particles as calculated with equation 3 of Throne and Meral (2008)

        :param a: Particle radius
        :param prob_dist: Distribution function for particle radius array a
        :param f_e: Form function
        :return: mean_f_e
        """

        first_integral = np.trapz(a * prob_dist, a)
        second_integral = np.trapz(a ** 2 * f_e ** 2 * prob_dist, a)
        third_integral = np.trapz(a ** 3 * prob_dist, a)

        mean_f_e = np.sqrt(first_integral * second_integral / third_integral)

        return mean_f_e


class SedimentSizeDistributionLogScale(SedimentSizeDistribution):

    def __init__(self, median_diameter, std_log):
        """
        
        :param median_diameter: Median diameter (D50), in millimeters
        :param std_log: Geometric standard deviation (log-scale) 
        """

        # create a lognormal distribution
        self._dist = lognorm(s=std_log, loc=0, scale=median_diameter)

        # get a CDF for the distribution
        alpha = 0.000001
        d_low_quantile = self._dist.ppf(alpha)
        d_high_quantile = self._dist.ppf(1-alpha)
        d_dist = np.logspace(np.log(d_low_quantile), np.log(d_high_quantile), 1000, base=np.e)
        cdf = self._dist.cdf(d_dist)

        super().__init__(d_dist, cdf)

    def get_mean_diameter(self, distribution='volume'):
        """
        
        :return: 
        """

        if distribution == 'volume':

            mean_diameter = self._dist.mean()

        else:

            mean_diameter = super().get_mean_diameter(distribution)

        return mean_diameter

    def get_median_diameter(self, distribution='volume'):
        """
        
        :return: 
        """

        if distribution == 'volume':

            median_diameter = self._dist.median()

        else:

            median_diameter = super().get_median_diameter(distribution)

        return median_diameter


class SedimentSizeDistributionPhiScale(SedimentSizeDistributionLogScale):

    def __init__(self, median_diameter, sigma_phi):
        """
        
        :param median_diameter: Median diameter (D50), in millimeters
        :param sigma_phi: Geometric standard deviation (phi-scale)
        """

        # scale the phi transform standard deviation so it can be used in a lognormal distribution
        std_log = np.log(2) * sigma_phi

        super().__init__(median_diameter, std_log)
