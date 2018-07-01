import xmltodict
from mudskipper import Client as Client_base
from mudskipper.connection import Connections as Connections_base
from tetrapod.bgc.endpoint import Endpoint
from tetrapod.bgc.exceptions import (
    BGC_exception_base, BGC_us_one_trace_exception )
from tetrapod.pipelines import (
    Transform_keys_camel_case_to_snake, Guaranteed_list,
    Remove_xml_garage, Replace_string, Compress_dummy_list,
    Parse_full_dict_date, Parse_partial_dict_date,
    Expand_dict_with_start_with,
)


class Connections( Connections_base ):
    pass


class Client( Client_base ):
    """
    Client for use the api of bgc without pain

    Notes
    =====
    `online doc <https://direct2m.backgroundchecks.com/
    TestHarness/docs/v4.14/BGCDirect_online_help.htm>`_
    """
    COMMON_PIPELINE = (
        Remove_xml_garage | Replace_string( 'YES', True )
        | Replace_string( 'NO', False ) | Transform_keys_camel_case_to_snake
        | Guaranteed_list( 'errors', 'names', 'addresses', 'records' )
        | Compress_dummy_list( 'errors', 'names', 'addresses', 'records' )
        | Parse_full_dict_date | Parse_partial_dict_date
        | Expand_dict_with_start_with( 'street', 'street_' ) )

    def us_one_validate( self, *args, ssn, _use_factory=None, **kw ):
        """
        return the result of the product USOneValidate from bgc

        arguments
        =========
        ssn: str

        _use_factory: py:class:`factory.Factory`
            used for ignore the call to bgc and try to parse
            the factory result

        Returns
        =======
        dict

        Raises
        ======
        py:class:`tetrapod.bgc.exceptions.BGC_exception_base`
        """
        if _use_factory is not None:
            native_response = { 'bgc': _use_factory.build() }
        else:
            body_xml = self.build_us_one_validate( ssn )
            response = self.endpoint.post( body=body_xml )
            native_response = response.native

        clean_data = self.COMMON_PIPELINE.run( native_response )
        self.validate_response( clean_data )

        root = clean_data[ 'bgc' ]
        order = root[ 'product' ][ 'us_one_validate' ]
        response = order[ 'response' ][ 'validation' ]
        return {
            'order_id': root[ 'order_id' ],
            'order': order[ 'order' ],
            'is_deceased': response[ 'is_deceased' ],
            'is_valid': response[ 'is_valid' ],
            'state_issued': response[ 'state_issued' ],
            'text_response': response[ 'text_response' ],
            'year_issued': response[ 'year_issued' ],
        }

    def us_one_trace(
            self, *args, ssn, first_name, last_name,
            _use_factory=None, **kw ):
        """
        return the result of the product USOneTrace from bgc

        arguments
        =========
        ssn: str
        first_name: str
        last_name: str

        _use_factory: py:class:`factory.Factory`
            used for ignore the call to bgc and try to parse
            the factory result

        Returns
        =======
        dict

        Raises
        ======
        py:class:`tetrapod.bgc.exceptions.BGC_exception_base`
        py:class:`tetrapod.bgc.exceptions.BGC_us_one_trace_exception`
        """
        if _use_factory is not None:
            native_response = { 'bgc': _use_factory.build() }
        else:
            body_xml = self.build_us_one_trace(
                ssn=ssn, first_name=first_name, last_name=last_name )
            response = self.endpoint.post( body=body_xml )
            native_response = response.native

        clean_data = self.COMMON_PIPELINE.run( native_response )
        self.validate_response( clean_data )
        self.validate_response_us_one_trace( clean_data )

        root = clean_data[ 'bgc' ]
        order = root[ 'product' ][ 'us_one_trace' ]
        response = order[ 'response' ]

        return {
            'order_id': root[ 'order_id' ],
            'order': order[ 'order' ],
            'records': response[ 'records' ],
        }

    @property
    def endpoint( self ):
        """
        build the endpoint using the current connection

        Returns
        =======
        py:class:`tetrapod.bgc.endpoint.Endpoint`
        """
        connection = self.get_connection()
        return Endpoint( connection[ 'host' ] )

    def validate_response( self, data ):
        """
        validate the general response from bgc

        Raises
        ======
        py:class:`tetrapod.bgc.exceptions.BGC_exception_base`
        """
        errors_raw = data[ 'bgc' ].get( 'response', {} ).get( 'errors', [] )
        errors = {
            error[ 'code' ]: error[ 'text' ] for error in errors_raw }
        if errors:
            raise BGC_exception_base( errors )

    def validate_response_us_one_trace( self, data ):
        """
        validate the response of the product UsOneTrace for errors

        Raises
        ======
        py:class:`tetrapod.bgc.exceptions.BGC_us_one_trace_exception`
        """
        errors_raw = (
            data[ 'bgc' ].get( 'product', {} ).get( 'us_one_trace', {} )
            .get( 'response', {} ).get( 'errors', [] ) )
        errors = { error[ 'code' ]: error[ 'text' ] for error in errors_raw }
        if errors:
            raise BGC_us_one_trace_exception( errors )

    def extract_loging_from_connection( self ):
        """
        retrieve the information of loging from the current connection

        Returns
        =======
        dict
        """
        connection = self.get_connection()
        return {
            'user': connection[ 'user' ],
            'password': connection[ 'password' ],
            'account': connection[ 'account' ]
        }

    def build_body( self ):
        """
        build the dict with the genral body and login for bgc

        Returns
        =======
        dict
        """
        loging = self.extract_loging_from_connection()
        return { 'BGC': {
            '@version': '4.14',
            '@xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
            '@xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'login': loging, } }

    def build_us_one_validate( self, ssn ):
        """
        build the xml for the us_one_validate when is not using the factory

        Arguments
        =========
        ssn: str

        Returns
        =======
        str
            a xml
        """
        product_body = {
            'product': {
                'USOneValidate': {
                    '@version': '1',
                    'order': {
                        'SSN': ssn,
                    },
                },
            },
        }
        body = self.build_body()
        body[ 'BGC' ].update( product_body )
        body_xml = xmltodict.unparse( body )
        return body_xml

    def build_us_one_trace( self, ssn, first_name, last_name ):
        """
        build the xml for the us_one_trace when is not using the factory

        Arguments
        =========
        ssn: str
        first_name: str
        last_name: str

        Returns
        =======
        str
            a xml
        """
        product_body = {
            'product': {
                'USOneTrace': {
                    '@version': '1',
                    'order': {
                        'SSN': ssn,
                        'firstName': first_name,
                        'lastName': last_name,
                    },
                },
            },
        }
        body = self.build_body()
        body[ 'BGC' ].update( product_body )
        body_xml = xmltodict.unparse( body )
        return body_xml
