package com.lballoy.ledger.presentation.rest;

import org.springframework.stereotype.Service;

import com.lballoy.ledger.presentation.rest.response.HealthResponse;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Service  
@Path("/")
public class LedgerEndpoint {
    @GET
    @Path("/health")
    @Produces(MediaType.APPLICATION_JSON)
    public Response health(){
        return Response.status(Response.Status.OK).entity(new HealthResponse("UP")).build();
    }
}
